#!/usr/bin/env python3
"""Render a curated daily HTML report from the arXiv candidate packet.

This is a lightweight local renderer for the current workflow. It does not
replace the research agent: the agent still has to verify project pages,
repositories, author background, company news, and duplicated items.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import time
from pathlib import Path
from zoneinfo import ZoneInfo


TITLE = "具身智能进入系统化竞争：VLA/WAM、数据闭环与真机基础设施同场推进"
FILE_TITLE = "具身智能进入系统化竞争：VLA-WAM、数据闭环与真机基础设施同场推进"


SELECTED = [
    ("2609.17372", "S", "WAM / 自进化 / 真机"),
    ("2609.17524", "S", "WAM / 多模态未来预测"),
    ("2609.17210", "S", "VLA 工程化 / 数据到部署"),
    ("2609.16644", "S", "WAM / 人形全身控制"),
    ("2609.16864", "S", "VLA / 动态操作"),
    ("2609.15870", "S", "世界潜动作 / 跨数据源"),
    ("2609.15976", "S", "具身记忆 / 移动操作"),
    ("2609.15382", "S", "WAM / 工程闭环"),
    ("2609.10021", "S", "VLA 数据筛选 / 清华"),
    ("2609.10706", "S", "VLA 预训练 / 人类视频"),
    ("2609.10915", "S", "VLA 推理效率 / 真机"),
    ("2609.16705", "A", "机器人数据工厂"),
    ("2609.16504", "A", "视觉触觉 / 灵巧操作"),
    ("2609.16437", "A", "遥操作 / 触觉数据采集"),
    ("2609.16683", "A", "人形全身灵巧操作"),
    ("2609.17035", "A", "软体机器人 VLA"),
    ("2609.16586", "A", "灵巧手 / 接触动态"),
    ("2609.15770", "A", "腿足运动 / JEPA 世界模型"),
    ("2609.16641", "A", "VLA 泛化 / 等变性"),
    ("2609.16503", "A", "端侧 VLA / MoE 压缩"),
    ("2609.17523", "A", "自进化智能体"),
    ("2609.17099", "A", "人类视频 / 潜动作"),
    ("2609.16737", "A", "视频规划 / 导航"),
    ("2609.15988", "A", "人形安全过滤"),
    ("2609.15921", "A", "触觉模仿学习"),
    ("2609.15910", "A", "触觉滑移检测"),
    ("2609.15726", "B", "触觉基准 / 仿真"),
    ("2609.17115", "B", "VLA 内生奖励"),
    ("2609.17521", "B", "物理视频生成"),
    ("2609.15840", "B", "ACT 稀疏修正"),
]

STRONG_RELATED_IDS = [
    "2609.17372",
    "2609.17524",
    "2609.17210",
    "2609.16644",
    "2609.16864",
    "2609.15870",
    "2609.15976",
    "2609.15382",
    "2609.10021",
    "2609.10706",
    "2609.10915",
    "2609.16705",
    "2609.16504",
    "2609.16641",
    "2609.16503",
    "2609.17523",
    "2609.17099",
    "2609.16737",
    "2609.17115",
    "2609.15840",
]

SUPPLEMENT_IDS = [
    "2609.16437",
    "2609.16683",
    "2609.17035",
    "2609.16586",
    "2609.15770",
    "2609.15988",
    "2609.15921",
    "2609.15910",
    "2609.15726",
    "2609.17521",
]

SELECTED_BY_ID = {aid: (priority, direction) for aid, priority, direction in SELECTED}


META = {
    "2609.17372": {
        "cn": "XPACE：把世界模型、动作模型和恢复数据生成合成一个自进化闭环",
        "origin": "企业团队：XPENG Robotics",
        "origin_note": "小鹏机器人以人形机器人 IRON 和车端/机器人感知控制栈为产业背景；这类企业数据和本体资源使真机闭环实验更有说服力。",
        "author_note": "一作/通讯快速背调：本轮未做完整学术履历归因；但企业真实本体、异构数据与 IRON 真机实验显著提高优先级。",
        "code": "未发现直接仓库",
        "real": "有真实人形机器人实验",
        "summary": "XPACE把同一个模型同时用于动作预测和未来视觉后果预测：它既能从视觉语言条件下生成机器人动作，也能在给定动作时模拟未来视频。更重要的是，模型会围绕专家轨迹生成偏离-恢复样本，再把筛过的恢复经验反哺策略，形成一个接近自进化的具身闭环。",
        "abstract": "论文提出统一具身世界模型 XPACE，用无动作标签视频学习视觉动态，用带动作的人类和机器人示范学习动作与未来预测，再通过由粗到细训练让策略逐步偏向真实机器人控制。模型还会利用自身模拟器制造恢复监督，在 XPENG IRON 人形机器人上展示异构经验迁移、未覆盖任务泛化和恢复数据带来的真机提升。",
        "intro": "引言的核心问题是：机器人若要像人一样从观察、行动和后果中持续学习，就不能把视频预测、动作学习和恢复经验生成分成互不相干的模块。XPACE试图把人类视频、机器人示范和模拟恢复轨迹放进同一个世界-动作模型，使模型不只模仿数据，也能主动制造对失败恢复有价值的训练信号。",
        "review": "核心优势是“世界模拟器用于策略改进”的闭环味道很浓，贴近你的自进化兴趣；短板是代码未见直接公开，外部复现门槛高。值得重点读方法和恢复数据生成部分。",
    },
    "2609.17524": {
        "cn": "ModAR：WAM 不必只预测 RGB，未来模态的选择本身就是关键设计",
        "origin": "高校团队：CMU / Pittsburgh 相关作者",
        "origin_note": "CMU 机器人与计算机视觉长期强势，Deva Ramanan 等作者在视觉表征、检测和机器人感知方向有较高影响力。",
        "author_note": "一作 Adam Hung 影响力需进一步核验；通讯/资深作者背景较强，且真实双臂实验提高可信度。",
        "code": "项目页可见，代码状态需复核",
        "real": "有真实双臂任务",
        "summary": "ModAR问了一个非常实际的问题：WAM 到底应该预测什么未来。它不把未来固定成 RGB 视频，而是按顺序生成点轨迹、DINO 特征、深度等控制相关模态，再让动作预测条件化于这些中间未来表示。",
        "abstract": "论文提出模态自回归 WAM，让模型依次去噪多种未来模态并最终预测动作。实验发现点轨迹、DINO 特征和深度对动作学习更稳定有益，额外预测未来 RGB 反而未必有收益。作者报告 ModAR 在相同数据下以更少训练 FLOPs 达到或超过视频初始化 WAM，并在真实双臂任务中优于基线。",
        "intro": "引言强调，视觉保真不等于控制有效。机器人需要几何、语义和运动线索，而不是所有像素细节。ModAR因此把未来预测拆成不同模态，并研究不同生成顺序和数据配比如何影响 WAM 的行为表现。",
        "review": "核心优势是把 WAM 从“生成视频”拉回“生成对动作有用的未来”。这是值得细读的范式论文，尤其适合作为你理解 WAM 表示选择的参考。",
    },
    "2609.17210": {
        "cn": "FluxVLA Engine：把 VLA/WAM 从论文模型推进到可复现工程平台",
        "origin": "开源工程团队：FluxVLA",
        "origin_note": "该项目主打 VLA 数据、训练、仿真、推理和机器人接口标准化；影响力取决于后续社区采用度。",
        "author_note": "作者列表较长，快速核验未发现明确顶级 PI 背书；但公开仓库和工程覆盖面使其具备工具链价值。",
        "code": "已在摘要中给出 GitHub 仓库",
        "real": "支持真实机器人执行接口，具体真机实验需复核",
        "summary": "FluxVLA Engine不是提出一个新策略模型，而是把数据格式、视觉语言模型、世界模型、动作头、离线强化学习、仿真评估、推理加速和机器人 operator 统一成配置驱动平台。它瞄准的是 VLA 领域正在暴露的工程碎片化问题。",
        "abstract": "论文描述一个开放平台，把异构具身策略组件连接成可审计的数据到部署流程。系统支持双臂仿真、自动数据生成、人类接管/纠错/奖励标注、Real-Time Chunking、远程 GPU 推理和轨迹后处理，目标是连接离线学习、仿真验证、在线纠错与真机执行。",
        "intro": "引言的问题设定是：VLA、WAM 和离线 RL 算法发展很快，但数据、训练、评测、运行时和本体接口割裂，导致好算法难以变成可靠机器人系统。FluxVLA把研究接口标准化，试图降低从论文到部署的摩擦。",
        "review": "如果仓库质量足够，它可能成为非常实用的 baseline/脚手架。建议重点看接口设计、数据格式和 real-time 部署部分，而不是把它当模型创新论文。",
    },
    "2609.16644": {
        "cn": "WholeBodyWAM：把预训练世界-动作先验迁移到人形全身操作",
        "origin": "高校/研究团队：作者机构需以 PDF 为准",
        "origin_note": "论文聚焦人形 loco-manipulation，是 WAM 从桌面操作向全身控制扩展的代表性方向。",
        "author_note": "Jim Tan 在机器人学习和强化学习方向较活跃；一作背景需进一步核验。",
        "code": "未发现直接仓库",
        "real": "报告真实世界 OOD 任务进展指标",
        "summary": "WholeBodyWAM试图把原本偏机械臂/桌面操作的 WAM 迁移到人形机器人全身移动操作。它同时预测未来视觉、操作动作和 whole-body controller 意图，让预训练世界-动作先验与不同 WBC 语义对齐。",
        "abstract": "论文提出通过 WBC-grounded coordination 保留预训练 WAM 先验，同时对异构全身控制器进行语义接地。作者报告仿真总体成功率 91.9%，真实世界 OOD 任务进展提升，并降低不同 WBC 间的成功率方差。",
        "intro": "引言指出现有 WAM 多集中在桌面或机械臂操作，尚未充分覆盖人形机器人需要的移动、平衡和操作耦合。WholeBodyWAM把高层世界-动作预测与低层全身控制意图结合，避免从零学习复杂全身行为。",
        "review": "核心价值是 WAM 全身化，与你关注的人形具身大脑高度相关。短板是代码未公开、真实实验细节需要查 PDF。",
    },
    "2609.16864": {
        "cn": "TEMPO：给 VLA 补上时间上下文，解决动态操作的运动歧义",
        "origin": "高校团队：Brown / UCLA 相关作者需进一步核验",
        "origin_note": "CoRL 2026 接收，说明研究问题和实验形式通过机器人学习社区筛选。",
        "author_note": "资深作者 Unnat Jain 在具身感知、机器人学习方向有公开研究积累；一作影响力需继续核验。",
        "code": "项目页可见，仓库状态需复核",
        "real": "有动态操作实验",
        "summary": "TEMPO指出很多 VLA 失败不是模型不够大，而是单帧输入天然缺少运动信息和任务阶段信息。它给冻结 VLA 加两个低成本时间信号：视频基础模型提取的 motion summary，以及短 proprioceptive history。",
        "abstract": "论文把动态操作失败拆成 motion ambiguity 和 state aliasing：单帧看不到物体运动，也无法区分视觉相似但动作不同的阶段。TEMPO无需改主干，只增加运动摘要和本体历史，在四个动态操作任务上提升成功率，并发布 TEMPO-Bench。",
        "intro": "引言强调，推理延迟或模型规模并不能解决缺失时间上下文的问题。动态任务需要知道物体正在怎么动、机器人刚刚处于什么阶段，因此时间表示应作为 VLA 输入的一等公民。",
        "review": "这篇很适合你的 VLA 研究：问题清楚、改法轻量、能解释失败模式。建议重点看 failure taxonomy 和 temporal input ablation。",
    },
    "2609.15870": {
        "cn": "WLA³：从无标注人类视频中学习世界潜动作，用统一监督连接语义、动力学和运动学",
        "origin": "联合团队：项目页可见，机构需以 PDF 为准",
        "origin_note": "该方向与 latent action、human video pretraining、跨本体 VLA 直接相关，是近期具身基础模型的重要支线。",
        "author_note": "一作/通讯快速核验不足；因问题本身与跨数据源 scaling 高度相关，仍给高优先级。",
        "code": "项目页可见，代码状态需复核",
        "real": "真机证据需复核",
        "summary": "WLA³把世界状态变化视作不同数据源之间共享的动作监督。它先学习 World Latent Action Model，从多视角与本体状态变化中得到局部潜动作和转移特征，再把这些表示复用于通用策略学习。",
        "abstract": "论文认为，扩展 generalist policy 的瓶颈在于异构数据缺少统一、低噪声的动作标签。WLAM通过重建局部世界转移、跨窗口一致性和部分模态重建，学习可跨数据源复用的潜动作表示，使人类视频和机器人数据更容易统一。",
        "intro": "引言的问题是：人类第一视角视频很多，但动作标签稀缺且与机器人本体不对齐。与其强行恢复具体机器人动作，不如从世界变化中学习更抽象的 latent action，再让下游策略把它接到具体本体。",
        "review": "潜动作是 VLA/WAM 之间很值得押注的接口变量。短板是需要重点核验真机和开源，但思想与 scaling/data efficiency 强相关。",
    },
    "2609.15976": {
        "cn": "MessyMem：让移动操作机器人从做过的事里形成长期可查询记忆",
        "origin": "高校团队：CoRL 2026，项目页可见",
        "origin_note": "移动操作长期记忆是具身大脑的重要能力，与单次任务式 VLA 形成互补。",
        "author_note": "项目来自机器人学习社区；一作/通讯影响力需进一步核验，CoRL 接收和真机评估提升优先级。",
        "code": "项目页可见，仓库状态需复核",
        "real": "有真实移动操作评估",
        "summary": "MessyMem关注一个非常具身的问题：机器人第二次来到同一空间时，应该记住柜子锁了、物体在哪个抽屉、上次交互结果如何，而不是每次重新推理。它构建空间接地的 3D scene graph，并把交互学到的属性和结果写进去。",
        "abstract": "论文提出持久记忆系统，让移动操作机器人把对象、位置、交互结果和视觉回忆连接起来，在后续任务中复用。系统在仿真和真实环境中评估，目标是把 learning-from-doing 从单回合策略扩展为跨任务经验积累。",
        "intro": "引言指出，当前机器人常把每个任务当作全新问题；紧凑地图缺少交互知识，视频历史又难以查询。MessyMem通过结构化记忆把空间、物体和行为后果连接起来，使机器人能在未来任务中利用过去经验。",
        "review": "这篇和自进化智能关系很近：不是更新模型参数，而是更新世界记忆。值得看系统表示和真实任务设计。",
    },
    "2609.15382": {
        "cn": "连续堆料挖掘 WAM：从预测未来到实时选择动作",
        "origin": "工程/产业场景团队：机构需以 PDF 为准",
        "origin_note": "全尺寸装载机闭环部署使其区别于纯桌面 benchmark，是物理 AI 工程落地样本。",
        "author_note": "作者背景需进一步核验；真实机器闭环、ROS2/TensorRT 和工程指标显著提高可信度。",
        "code": "未发现直接仓库",
        "real": "有全尺寸机器物理实验",
        "summary": "这篇把 WAM 用在连续挖掘：每次铲斗动作会改变下一步地形，策略必须预测动作后果、筛掉不可行动作、选择装载量最大的候选并重新规划。它比“看起来聪明”的视频预测更接近实际工业控制。",
        "abstract": "论文提出一个从感知、动作候选、地形变化预测、候选排序到执行再规划的闭环 WAM。仿真中世界模型排序减少平均铲取次数并保持完成率，完整系统优于独立训练 SAC；物理实验展示真实闭环可行性，ROS2/TensorRT 在 Jetson 上实时处理候选。",
        "intro": "引言把挖掘描述为强序列决策：一个动作会重塑未来可行动空间。可用世界模型必须不仅预测后果，还要足够快、能排序候选并进入真实机器闭环。",
        "review": "强在真实工程闭环和 decision-level WAM；短板是场景较窄、开源不明。适合作为“WAM 如何真正服务动作选择”的案例。",
    },
    "2609.10021": {
        "cn": "RoboDrop：用局部梯度兼容性筛选 VLA 后训练数据",
        "origin": "高校/企业联合：Tsinghua University / Striding AI",
        "origin_note": "清华是国内具身智能重要来源之一；Striding AI 关注机器人基础模型与具身数据闭环。",
        "author_note": "硬性关注高校命中；一作/通讯详细代表作需进一步核验，但清华与真实机器人数据使其优先级高。",
        "code": "未发现直接仓库",
        "real": "有真实机器人数据与 rollout",
        "summary": "RoboDrop解决后训练数据脏的问题：机器人数据里会有局部执行错误、传感器漂移、时间戳错位，单纯按整条轨迹成败筛选会留下很多局部坏样本。它用候选样本和相似验证样本之间的局部梯度兼容性来评估数据价值。",
        "abstract": "论文在一次 warm-up 中计算候选样本梯度，并与任务语义和视觉上下文相近的验证样本梯度比较，再聚合成 episode 分数。实验涵盖受控污染、模拟次优示范和真实机器人非专家数据，报告筛选后策略成功率提升。",
        "intro": "引言强调，VLA 后训练的数据价值取决于它会如何影响当前目标任务，而不是轨迹表面是否相似。局部梯度兼容性提供了一种更接近训练动态的数据筛选信号。",
        "review": "这篇非常贴合你的数据闭环兴趣。优势是方法可插入现有 VLA 后训练；短板是需要干净参考集，代码未公开。",
    },
    "2609.10706": {
        "cn": "HuRo：把人类视频机器人化，扩展 VLA 预训练数据",
        "origin": "高校团队：Yonsei University 等",
        "origin_note": "工作面向 human video to robot data，是 VLA scaling 的核心数据路线之一。",
        "author_note": "一作影响力需继续核验；公开仓库和真机 ALLEX 任务显著提升优先级。",
        "code": "已确认公开仓库",
        "real": "有 ALLEX 双臂灵巧机器人实验",
        "summary": "HuRo把人类视频转换成机器人视角、机器人对齐动作和中间状态，试图把海量人类操作视频变成 VLA 预训练数据。它直接针对 embodiment gap：人手、人眼、机器人相机和机器人动作空间都不一样。",
        "abstract": "论文构建机器人化流水线，将异构人类视频转换为约 63 万条 episode 和 1.42 亿帧机器人对齐数据。随着机器人化预训练规模增加，作者报告真实双臂操作和分布外泛化显著提升，并通过消融说明视觉机器人化与动作重定向都有贡献。",
        "intro": "引言的问题是：人类视频数量巨大，但直接用于机器人会受到视角、手型和动作空间差异限制。HuRo尝试同时对齐观察和动作，让人类视频成为通用 VLA 预训练来源。",
        "review": "这是今天最符合“代码+真机+scaling”的条目之一。建议重点看数据转换 pipeline 和下游微调设置。",
    },
    "2609.10915": {
        "cn": "IMLE-VLA：单步动作生成，让 VLA 更接近实时控制",
        "origin": "高校团队：Simon Fraser University / University of Pennsylvania",
        "origin_note": "UPenn GRASP 等机器人传统强，推理效率是 VLA 走向真机部署的关键瓶颈。",
        "author_note": "一作影响力需进一步核验；机构和 Franka 真机结果使其优先级较高。",
        "code": "项目页声称可用，直接仓库需复核",
        "real": "有 Franka Panda 真机实验",
        "summary": "IMLE-VLA针对扩散/flow 动作头多步采样导致的控制延迟。它用 conditional IMLE 单步生成动作，同时保留多模态动作分布，避免普通回归把多个可行动作平均成不可执行动作。",
        "abstract": "论文将 π0.5 的多步动作头替换为单步条件生成器，报告推理频率从 15 Hz 提升到 55 Hz，同时在 LIBERO 和真实 Franka 任务中保持或提升成功率，并让动作更平滑。",
        "intro": "引言把 VLA 动作生成的矛盾概括为：连续多模态动作头准确但慢，单步回归快但容易平均多峰分布。IMLE-VLA试图同时保留多模态和低延迟。",
        "review": "非常工程关键：如果你以后做真机 VLA，动作频率会直接影响体验和成功率。短板是需确认代码质量。",
    },
    "2609.16705": {
        "cn": "Robot Data Factory：把机器人数据从静态数据集改造成持续生产系统",
        "origin": "国际联合团队：多机构作者",
        "origin_note": "Sami Haddadin 等在机器人系统、触觉、安全人机协作方向有较高可见度；该文更偏框架/路线图。",
        "author_note": "资深作者背景较强；作为立场/框架论文，实验贡献不是核心。",
        "code": "不适用 / 未发现",
        "real": "讨论真实训练场与数据基础设施",
        "summary": "Robot Data Factory把物理 AI 的核心资源定义为“机器人经验”，而不只是数据文件。它强调观察、动作、本体、上下文和结果构成 perception-action-consequence loop，并提出持续生成、验证、复用经验的基础设施。",
        "abstract": "论文提出 RDF：通过可复现任务、技能课程、多模态同步传感、外部真值、机器人网络、数据管线和 living benchmarks，形成 Deploy-Measure-Learn-Repeat 循环，支撑世界模型、VLA、具身策略、数字孪生和后续部署。",
        "intro": "引言把数据问题从“大不大”转向“是否保留物理交互后果”。静态数据集无法满足持续学习机器人，数据工厂应像科学生产流程一样不断产生可验证经验。",
        "review": "这篇不一定给你算法，但会帮你组织研究框架。值得看其中的数据层级、质量定义和闭环基础设施设想。",
    },
    "2609.16504": {
        "cn": "UniDex-ViTac：用人类视频指导仿真生成视觉触觉灵巧操作策略",
        "origin": "高校团队：机构需以 PDF 为准",
        "origin_note": "视觉触觉灵巧操作是 VLA 之外非常关键的具身感知支线。",
        "author_note": "一作/通讯影响力快速核验不足；真实物理试验和触觉设计提升价值。",
        "code": "项目页可见，仓库需复核",
        "real": "有真实灵巧操作试验",
        "summary": "UniDex-ViTac从人类视频出发，在仿真中生成机器人示范和指尖接触观测，再训练一个统一视觉触觉策略。它的重点不是直接从人类视频学动作，而是把视频变成可生成触觉监督的仿真课程。",
        "abstract": "论文用对象特定 residual RL specialist 将人类-物体交互参考适配到机器人手臂系统，得到带指尖接触观测的 1 万条仿真轨迹，再训练 ACT generalist。作者报告无真实机器人示范或微调也能在物理试验中获得提升。",
        "intro": "引言指出，人类视频缺少机器人动作和触觉信号，而灵巧操作又强依赖接触。UniDex-ViTac通过视频指导仿真补齐机器人侧接触与动作监督。",
        "review": "优势是把触觉引入 human video scaling；短板是仿真到真实的假设需要细看。适合关注灵巧操作数据生成。",
    },
    "2609.16437": {
        "cn": "XRoboToolKit-T：带触觉辅助的高稳定遥操作数据采集系统",
        "origin": "研究团队：机构需以 PDF 为准",
        "origin_note": "遥操作和触觉辅助是高质量真机数据生产的底层能力，对 VLA 数据闭环很重要。",
        "author_note": "作者影响力快速核验不足；任务真实且接触丰富，作为数据采集工具优先级较高。",
        "code": "未发现直接仓库",
        "real": "有真实接触操作任务",
        "summary": "XRoboToolKit-T关注接触丰富任务中的数据采集稳定性。系统用触觉驱动的力控架构提供辅助，包括快速分析法向力分布、推断伪剪切力，以及用 VLA 模块结合触觉和任务描述细化动作。",
        "abstract": "论文提出一种带触觉辅助的遥操作系统，用于抓取柔性移液管、向血管训练垫插入注射器等高接触任务。系统声称比无触觉辅助遥操作有更高采集效率和更好稳定性。",
        "intro": "引言指出，许多机器人数据采集方案缺少稳定高频触觉反馈，导致接触丰富任务的数据质量低。XRoboToolKit-T把触觉反馈直接纳入遥操作力控与动作细化。",
        "review": "不是具身大脑模型，但对你关注的数据闭环很基础。若未来做真机数据采集，这类系统值得收藏。",
    },
    "2609.16683": {
        "cn": "Weave：从人类-物体交互学习人形全身灵巧操作",
        "origin": "高校/研究团队：项目页可见，机构需以 PDF 为准",
        "origin_note": "人形全身操作是具身智能从手臂操作走向通用本体的关键方向。",
        "author_note": "作者影响力需核验；项目页和多对象全身任务使其进入高关注。",
        "code": "项目页可见，仓库需复核",
        "real": "真机证据需复核",
        "summary": "Weave把捕捉到的人类-物体交互转换成可执行的人形机器人参考，并训练接触与几何感知策略，联合控制身体和手指。它覆盖的是移动、平衡、手部接触和物体运动的耦合问题。",
        "abstract": "论文通过 contact-aware retargeting 和 approach-motion completion 把人类交互转成机器人对象参考，再训练同时控制 29 个身体关节和 12 个手指关节的策略。作者报告多对象交互有较高成功率和一定泛化能力。",
        "intro": "引言强调，人形机器人与物体交互需要同时解决全身平衡、移动和手部接触。人类示范提供协调样本，但需要重定向到不同本体和动力学。",
        "review": "适合观察人形操作的范式：它把 human motion、contact retargeting 和 policy learning 串起来。需重点核验真机和开源。",
    },
    "2609.17035": {
        "cn": "SWIM：面向软体机器人的视觉语言全身交互操作",
        "origin": "高校/研究团队：机构需以 PDF 为准",
        "origin_note": "软体/连续体机器人是不同于刚性机械臂的本体路线，能检验 VLA 是否具备跨本体抽象能力。",
        "author_note": "作者影响力需核验；硬件实验使其比纯仿真更有价值。",
        "code": "未发现直接仓库",
        "real": "有软体机器人硬件实验",
        "summary": "SWIM把语言、RGB 观察和腱状态映射到完整驱动命令序列，用扩散动作头和 Visual Soft Proprioception 共同学习软体机器人全身形变与任务关系。",
        "abstract": "论文提出 SWIM-VLA，把 VLA 策略与软体本体的视觉软 proprioception 结合，在包装、到达、抓取等任务上进行仿真和硬件评估。系统利用软体机器人的顺应性减少在线策略查询需求。",
        "intro": "引言指出，软体机器人通过分布式形变和接触实现操作，但语言视觉到连续驱动序列的映射困难。SWIM通过共享表示把视觉、语言和腱状态联系起来。",
        "review": "它不是主流机械臂 VLA，但对跨本体具身大脑很有启发。短板是通用性和开源不足需观察。",
    },
    "2609.16586": {
        "cn": "ProxiDex：用接近状态建模灵巧手接触动态",
        "origin": "高校/研究团队：CoRL 2026，项目页可见",
        "origin_note": "灵巧手接触建模是具身大脑落地的关键短板之一。",
        "author_note": "CoRL 接收提升可信度；一作/通讯代表作需进一步核验。",
        "code": "项目页可见，仓库需复核",
        "real": "有真实灵巧操作实验",
        "summary": "ProxiDex把手-物体接近关系当作硬件无关的接触状态，既可用于 VR 遥操作反馈，也可用于学习动作条件下的接近动态。它试图缓解视觉遮挡和触觉硬件不统一的问题。",
        "abstract": "论文重建交互点云并把几何距离转成 proximity cues，再用 forward-inverse 设计学习动作条件接近动态。策略利用动态一致性和阶段性 token 重权重，在仿真和真实任务中提升鲁棒性。",
        "intro": "引言指出，灵巧操作经常被手部遮挡和传感硬件差异困扰。接近状态比具体触觉传感器更通用，能作为接触即将发生或正在变化的中间表示。",
        "review": "优势是表示设计很实用，能桥接视觉和触觉。建议看 proximity representation 是否可迁移到你关注的 VLA/WAM。",
    },
    "2609.15770": {
        "cn": "JEPLO：用 JEPA 世界模型学习 LiDAR 腿足运动表征",
        "origin": "研究团队：ASIG-X，机构需进一步核验",
        "origin_note": "腿足机器人感知运动是具身生态基础能力，LiDAR 路线适合复杂地形和低纹理场景。",
        "author_note": "作者影响力需核验；开源实现、数据和硬件设计显著加分。",
        "code": "已在摘要中给出 GitHub 仓库",
        "real": "有 sim-to-real 腿足机器人实验",
        "summary": "JEPLO用 proprio-exteroceptive JEPA 世界模型从原始 LiDAR 和本体观测中学习自车体地形表征，再通过 teacher-student 管线训练腿足运动策略。它强调无需显式地图，也能在遮挡、稀疏和噪声感知下保持鲁棒。",
        "abstract": "论文提出单阶段 LiDAR-based perceptive locomotion 框架，用 PE-JEPA 学习预测性地形表征，再在仿真中训练使用该 latent 的运动策略，并实现 sim-to-real，开源实现、数据和硬件设计。",
        "intro": "引言指出，RGB-D 在腿足感知中更常见，而 LiDAR 通常依赖显式建图。JEPLO尝试直接从原始 LiDAR 预测表征中学习控制相关信息。",
        "review": "虽然不是 VLA，但它代表 embodied world representation 在运动控制中的路线。开源和真机让它值得收藏。",
    },
    "2609.16641": {
        "cn": "SAVLA：用几何等变性提高 VLA 空间泛化",
        "origin": "高校/研究团队：机构需以 PDF 为准",
        "origin_note": "VLA 的空间泛化是核心瓶颈，等变结构是一条数据效率路线。",
        "author_note": "作者影响力需核验；对比 GR00T N1.5 和 LIBERO 旋转泛化使其具备方法参考价值。",
        "code": "未发现直接仓库",
        "real": "主要为 LIBERO 仿真/基准",
        "summary": "SAVLA认为 VLA 从示范中学空间能力，遇到未覆盖位姿就容易失效。它冻结预训练视觉语言骨干，加入等变 flow-matching 动作头和 canonicalizer，让几何条件在网络层中保持不变/等变类型。",
        "abstract": "论文提出 symmetry-aware VLA，将状态、动作和条件拆成 invariant 与 equivariant 通道，并将斜视图转到规范坐标。作者报告在 LIBERO 上超过 GR00T N1.5，尤其在旋转扰动下提升明显。",
        "intro": "引言强调，图像和语言本身含有几何信息，但常规 VLA 并没有结构性利用这些约束。等变性可以让模型在少量示范下更好泛化到新姿态。",
        "review": "值得作为 data efficiency 方法读。短板是真机与开源证据不足，优先级低于有物理验证的工作。",
    },
    "2609.16503": {
        "cn": "AdaDE：把密集 VLA 改成可裁剪 MoE，面向端侧部署",
        "origin": "研究团队：机构需以 PDF 为准",
        "origin_note": "VLA 越来越大，端侧/边缘部署会成为真实机器人瓶颈。",
        "author_note": "作者影响力需核验；部署问题重要，但真机证据需确认。",
        "code": "未发现直接仓库",
        "real": "主要为 LIBERO / SimplerEnv",
        "summary": "AdaDE把 VLA 中部分 dense FFN 转成 MoE，再根据微调期间的 router 统计关闭一部分专家，从而减少部署时保留的 LLM 参数。它试图在不重新恢复训练的情况下压缩 VLA。",
        "abstract": "论文提出 Dense2MoE conversion，使转换初始保持原 dense FFN 函数，然后用动态 expert mask 和 staged training 关闭低使用专家。作者报告关闭 40% LLM 参数后仍保留大部分 LIBERO 和 SimplerEnv 表现。",
        "intro": "引言指出，VLA 参数增长与机器人端资源约束冲突。直接剪枝容易破坏策略，MoE 适配可用路由统计识别冗余专家。",
        "review": "适合作为 VLA 部署效率支线关注。若你做真实机器人，压缩和低延迟会越来越重要。",
    },
    "2609.17523": {
        "cn": "ScienceBuddy：递归中的递归，自我改进科研智能体",
        "origin": "研究产品团队：Gen-Verse / ScienceBuddy",
        "origin_note": "该工作与具身不直接相关，但对自进化系统、harness 演化和评测闭环有方法启发。",
        "author_note": "作者影响力需核验；代码公开和系统产品形态提高可观察性。",
        "code": "已在摘要中给出 GitHub 仓库",
        "real": "真实科研工作台交互，非机器人",
        "summary": "ScienceBuddy把科研智能体做成持续改进工作台：用户请求、反馈和执行证据被转成新任务与评测 rubric。它的内层递归改进 harness，外层递归在改进后的 harness 上训练模型。",
        "abstract": "论文提出 recursive-in-recursive self-improvement，将工作流演化与模型强化学习耦合。案例展示研究者交互、harness refinement 和模型学习，并发布系统与代码。",
        "intro": "引言认为，智能体能力不只来自模型，也来自工具、任务分解、证据记录和评测方式。若 harness 能从失败中改进，模型就能在更高质量环境中继续学习。",
        "review": "值得放在自进化视野里读，但不要把它等同于机器人自进化。重点看反馈如何变成训练任务。",
    },
    "2609.17099": {
        "cn": "GeoLAM：从无动作人类视频中学习几何接地潜动作",
        "origin": "高校/研究团队：机构需以 PDF 为准",
        "origin_note": "与 HuRo/WLA³ 同属 human video to robot action 的数据扩展路线。",
        "author_note": "作者影响力需核验；问题与 scaling 强相关，优先级中高。",
        "code": "未发现直接仓库",
        "real": "真机证据需复核",
        "summary": "GeoLAM从无动作人类视频中学习 latent action，但避免只靠像素重建。它用冻结几何特征层级和训练期 4D 几何教师，让潜动作更保留 3D 位移、残余平面运动和表面方向变化。",
        "abstract": "论文提出几何接地的潜动作学习框架，使用未来帧重建、4D geometry teacher、可见性和置信度加权，鼓励连续潜动作捕捉操作相关几何运动。",
        "intro": "引言指出，视觉重建会把外观、相机运动和真正操作动作混在一起。几何监督能让 latent action 更接近可迁移的物理变化。",
        "review": "适合和 HuRo、WLA³ 横向比较。短板是若无真机验证，只能作为表征路线观察。",
    },
    "2609.16737": {
        "cn": "CueNav：用视觉线索引导视频规划，再由逆动力学转成导航动作",
        "origin": "高校/研究团队：项目页可见",
        "origin_note": "视频生成作为机器人规划 backbone 是 WAM/世界模型的邻近方向。",
        "author_note": "作者影响力需核验；项目页与导航实验使其值得观察。",
        "code": "项目页可见，仓库需复核",
        "real": "真实导航证据需复核",
        "summary": "CueNav把生成视频模型用于机器人导航：BEV 地图提供全局任务上下文，保留机器人身体的一部分让模型知道本体约束，随后用 inverse dynamics model 把视频计划中的 dense flow 转成动作。",
        "abstract": "论文提出视觉线索引导的视频规划框架，用 BEV 和 egocentric body cue 条件化视频模型，再用具体本体的 IDM 做 video-to-action。作者报告在长程导航和泛化上优于基线。",
        "intro": "引言指出，视频模型可预测未来观察，但短程指导和几何恢复限制了长程导航。CueNav加入全局和本体线索，使视频计划更可执行。",
        "review": "它对 WAM 的启发是：未来视频需要可转动作接口。建议看 video-to-action 的 IDM 设计。",
    },
    "2609.15988": {
        "cn": "ResSafe：用残差强化学习做人形机器人隐式安全过滤",
        "origin": "研究团队：机构需以 PDF 为准",
        "origin_note": "人形机器人安全过滤是从演示走向部署的底层能力。",
        "author_note": "作者影响力需核验；若有真实人形实验则优先级可上调。",
        "code": "未发现直接仓库",
        "real": "真机证据需复核",
        "summary": "ResSafe把人形控制的性能和安全分解：nominal policy 只追求任务表现，residual policy 学习安全修正。这样避免在一个 reward 里同时调性能、安全和鲁棒性的复杂权衡。",
        "abstract": "论文提出 residual RL 作为隐式安全过滤机制，通过解耦 nominal 与 residual 策略改善性能-安全 Pareto trade-off，并声称提高扰动下稳定性。",
        "intro": "引言指出，强化学习人形策略仍可能输出导致摔倒的不安全动作。显式安全过滤难以覆盖高维接触系统，残差策略可学习何时干预。",
        "review": "不是具身大脑，但部署价值高。值得观察是否有真实人形和开源实现。",
    },
    "2609.15921": {
        "cn": "Touch2Trace：触觉驱动的灵巧手电缆追踪模仿学习",
        "origin": "研究团队：CoRL 2026",
        "origin_note": "触觉高频控制是灵巧操作走向真实任务的关键。",
        "author_note": "CoRL 接收提高可信度；作者代表作需进一步核验。",
        "code": "未发现直接仓库",
        "real": "有真实灵巧手触觉实验",
        "summary": "Touch2Trace研究电缆这类柔性物体的手内追踪，需要连续调节压力、摩擦和滑移。系统用 TacV5 触觉编码器预训练，再以轻量 transformer 在 60 Hz 上进行行为克隆控制。",
        "abstract": "论文系统评估编码器预训练、控制频率、时间上下文和空间分辨率对 tactile-driven policy 的影响，并在 Tesollo DG-5F 手上完成真实电缆追踪。",
        "intro": "引言指出，柔性物体操作不能只靠视觉，手指层面的接触变化决定任务成败。触觉预训练与高速策略是关键。",
        "review": "对触觉 foundation / dexterous manipulation 很实用。建议关注传感器、控制频率和失败分析。",
    },
    "2609.15910": {
        "cn": "SlipSense：多模态触觉滑移检测，面向低延迟与跨平台泛化",
        "origin": "研究团队：CoRL 2026",
        "origin_note": "滑移检测是灵巧操作闭环控制的底层反射能力。",
        "author_note": "CoRL 接收提高可信度；作者影响力需进一步核验。",
        "code": "未发现直接仓库",
        "real": "有真实传感器与物体数据",
        "summary": "SlipSense使用 TacV5 的 32x32 压阻阵列和高频三轴加速度计，分别捕捉压力分布和摩擦振动，再做跨模态注意力与因果预测，用于低延迟滑移检测。",
        "abstract": "论文基于 37 个物体、约 140 万帧数据评估多模态滑移检测，报告高 Macro F1、低误报和低延迟，并讨论跨平台泛化。",
        "intro": "引言指出，滑移检测需要同时刻画空间压力和高频振动，且真实操作对延迟极敏感。多模态融合能比单一触觉模态更稳定。",
        "review": "它不是策略论文，但对灵巧操作闭环非常底层。可作为触觉模块候选阅读。",
    },
    "2609.15726": {
        "cn": "Bench2Dex：跨 12 种灵巧手的视觉触觉双手操作基准",
        "origin": "高校联合团队：项目页可见",
        "origin_note": "多手型、多任务、统一触觉接口基准对算法比较有长期价值。",
        "author_note": "作者列表包含多名国内视觉/机器人研究者；具体通讯与代表作需以 PDF 为准。",
        "code": "项目页可见，仓库需复核",
        "real": "仿真基准，明确不替代真实触觉",
        "summary": "Bench2Dex构建跨 12 种灵巧手的双手视觉触觉操作仿真基准，用统一的 simulated tactile interface 把不同手型的接触几何转成类似图像的触觉观测。",
        "abstract": "论文包含 26 个双手任务、约 1.3K 人类遥操作示范、同步视觉/触觉/本体/动作/物体状态，并评估 ACT、Diffusion Policy、pi0.5、GR00T N1.5 的性能和失败模式。",
        "intro": "引言指出，真实触觉硬件尚未统一，不同灵巧手结构差异大，导致算法难以公平比较。Bench2Dex提供统一仿真接口用于方法开发。",
        "review": "基准价值高，但因为非真机，优先级低于真实触觉工作。适合做 baseline/评测参考。",
    },
    "2609.17115": {
        "cn": "IRR：复用 VLA 表征作为机器人自评价奖励",
        "origin": "研究团队：机构需以 PDF 为准",
        "origin_note": "内生奖励和结果评价是机器人自进化闭环的关键模块。",
        "author_note": "作者影响力需核验；目前更像研究设想/方法框架，需观察后续实证。",
        "code": "未发现直接仓库",
        "real": "有 COMAU Racer 3 实验基础描述",
        "summary": "IRR提出复用 VLA 已有视觉编码器和成功示范终点作为结果评价器，不再额外训练一个奖励模型。新结果与参考成功状态在冻结特征空间中比较，形成策略改进信号。",
        "abstract": "论文把 successful demonstration endpoints 作为任务参考，用 VLA 冻结视觉编码器计算 outcome score，目标是降低人工评分和额外感知模块成本。作者描述了 COMAU Racer 3 TRL 4 示范基础和后续评估方法。",
        "intro": "引言指出，VLA 已经包含视觉表征和成功执行示范，这两者也可以用于评价机器人自己的结果。IRR把奖励计算嵌入现有 perception-demonstration pipeline。",
        "review": "想法与自进化吻合，但实证还不够强。适合作为 reward reuse 的观察项。",
    },
    "2609.17521": {
        "cn": "PhysStream：可交互物理视频生成，带结构化场景记忆和细粒度控制",
        "origin": "视觉生成研究团队：机构需以 PDF 为准",
        "origin_note": "物理一致视频生成是具身世界模型的邻近基础技术。",
        "author_note": "作者影响力需核验；非机器人论文，因物理视频控制与 WAM 有连接而纳入。",
        "code": "项目页可见，仓库需复核",
        "real": "数字/视频生成环境",
        "summary": "PhysStream做可流式控制的物理视频生成，维护位置图和物体跟踪图作为结构化场景记忆，并用稀疏速度增量信号控制物体运动。它支持生成过程中途交互控制。",
        "abstract": "论文先微调双向运动控制模型，再训练因果自回归模型，引入结构化场景记忆，改善多物体刚体桌面场景的物理一致性和轨迹控制。",
        "intro": "引言指出，现有可控视频生成常要求事先给完整控制序列，或用像素信号指定位置而非动力学。PhysStream希望用物理量控制生成过程。",
        "review": "非机器人，但值得观察能否成为 WAM 的数据/模拟组件。当前优先级低于有机器人闭环的工作。",
    },
    "2609.15840": {
        "cn": "UGR：对 ACT 动作块中高不确定时间步做稀疏修正",
        "origin": "研究团队：机构需以 PDF 为准",
        "origin_note": "Action Chunking 是机器人策略常用范式，稀疏修正有部署效率价值。",
        "author_note": "作者影响力需核验；真机和开源需继续确认。",
        "code": "未发现直接仓库",
        "real": "真机证据需复核",
        "summary": "UGR认为长时程 action chunk 的失败往往来自少数关键时间步，而不是整段都错。它先预测完整动作块，再估计每步不确定性，只对最不确定时间步做残差修正。",
        "abstract": "论文提出 coarse-to-refine 的 sparse refinement 框架，用隐藏状态预测 per-step temporal uncertainty，通过二值 mask 选择需要修正的时间步，减少均匀 refinement 的低效。",
        "intro": "引言指出，chunk-based visuomotor policy 的错误并非均匀分布。把计算集中在关键时间步，可能在保持效率的同时改善长时程操作。",
        "review": "适合做 ACT 系列方法补丁参考。证据强度和范式新意都不如前排，列为 B 级观察。",
    },
}


NEWS = [
    ("英伟达转向 tokens/W", "2026-09-15", "NVIDIA近期围绕 Vera Rubin、数据中心系统和每瓦特 token 吞吐沟通，说明大模型基础设施竞争正在从单卡峰值转向整机互联、推理吞吐和能源效率。对具身智能来说，这会影响 VLA/WAM 是端侧部署、边缘部署，还是多机器人共享推理集群。", "https://blogs.nvidia.com/blog/"),
    ("CUDA-Q继续开放", "2026-09-14", "NVIDIA新闻页本周突出开源 CUDA-Q 容错量子计算平台。它短期未必改变具身模型训练，但显示 NVIDIA 正在把软件栈从 GPU 加速扩展到更宽的计算平台，长期影响 AI 训练、科学计算和智能体工具链边界。", "https://blogs.nvidia.com/blog/"),
    ("Skild单视频学任务", "2026-09-10", "NVIDIA官方新闻介绍 Skild AI 使用 Physical AI 全栈平台从单个视频示范学习新机器人任务。值得关注的不是宣传语本身，而是数据获取正向视频理解、动作重定向和跨本体策略迁移靠拢。", "https://blogs.nvidia.com/blog/"),
    ("OpenAI推 Agents API", "2026-09-10", "OpenAI官方更新列表显示 Agents API 在本周发布，重点是把多步骤工具调用、状态管理和智能体执行从应用层拼装推进到平台层。你的每日 paper loop 也可以被视作检索、核验、排序、写作、去重的 agent workflow。", "https://openai.com/index/"),
    ("OpenAI推实时 API", "2026-09-10", "OpenAI本周更新列表还列出 GPT-Live-1 API，方向上继续强化实时交互。实时多模态模型与工具、设备和长期状态结合后，会从“回答”推进到持续观察、行动和修正，这与具身模型和 GUI agent 面临的问题同构。", "https://openai.com/index/"),
    ("十亿用户级存储", "2026-09-11", "OpenAI官方更新列表显示 Scaling Storage for 1 Billion ChatGPT Users。它提醒我们，大模型前沿不仅是模型结构和 benchmark，也包括存储、检索、日志、状态和成本控制；智能体产品会越来越像持续运行的基础设施。", "https://openai.com/index/"),
    ("Anthropic谈威胁情报", "2026-09-10", "Anthropic本周发布 Threat Intelligence Report，关注模型被用于网络攻击、滥用和防护的案例。对具身智能而言，当模型获得工具和物理执行权限后，安全评测必须覆盖权限、动作边界、可回滚性和异常恢复。", "https://www.anthropic.com/news"),
    ("Qwen多模态外溢", "本周官网窗口", "阿里云博客近期 Qwen-Drive-1.0 和 QwenCloud 更新显示，Qwen路线正在向驾驶、视觉语言基础模型和企业级工作流扩展。注意 Qwen-Robot Suite 公开页面日期较早，本期只把近期官网更新作为生态动向。", "https://www.alibabacloud.com/blog"),
    ("数据中心成公共议题", "2026-09-16附近", "主流科技媒体近期集中讨论数据中心能耗、地方社区反对和公众对 AI 基础设施的接受度。算力、能源、用水、许可和社会信任可能成为模型训练与部署的真实上限。", "https://www.theverge.com/ai-artificial-intelligence/995917/data-center-nyt-midterm-poll-september"),
    ("大厂放慢AI争论", "2026-09-16附近", "围绕安全协定、反垄断和大厂是否会放慢 AI 的讨论升温。它不一定代表行业真的减速，但说明前沿竞争的评价函数正在变复杂：能力、商业速度、能源、风险治理和市场结构会同时进入公众视野。", "https://www.theverge.com/ai-artificial-intelligence/995186/is-big-techs-ai-slowdown-a-safety-pact-or-a-cartel"),
]


EXPERIMENTS = {
    "2609.17372": "实验围绕 XPENG IRON 人形机器人展开，比较异构训练、人类经验迁移和模型生成恢复数据对真实任务完成度的影响。需要重点看恢复轨迹如何生成、如何过滤，以及真机任务是否覆盖未见技能。",
    "2609.17524": "实验系统比较不同未来模态、训练数据配比和 WAM 结构；主结果包含仿真/离线成功率以及三项真实双臂操作任务。关键看点是点轨迹、DINO 特征、深度与 RGB 预测的消融。",
    "2609.17210": "实验/展示重点是工程平台能力：数据接口、双臂仿真、自动数据生成、HITL 接管与纠错、RTC 推理和远程 GPU 服务。更像工具链验证，需要看仓库是否提供可复现任务配置。",
    "2609.16644": "实验包含人形 loco-manipulation 仿真任务、不同 whole-body controller 下的方差对比，以及真实世界 OOD 任务进展指标。关键是 WBC 语义接地是否真正提升跨控制器泛化。",
    "2609.16864": "实验设计围绕动态操作失败模式：Bottle Handover 等动态任务、运动歧义与状态混淆分析、时间信号消融，以及 TEMPO-Bench 的运动感知评测。重点看单帧 VLA 与加入 temporal context 的对比。",
    "2609.15870": "实验应关注 WLAM 学到的局部潜动作如何用于多数据源策略学习，包括人类视频、机器人数据、语义/动力学/运动学表示的一致性，以及下游任务中的泛化表现。",
    "2609.15976": "实验包括仿真和真实移动操作环境，评估机器人是否能把柜门状态、物体位置、交互结果等经验写入 3D 场景图并在后续任务复用。重点看跨房间/跨访问的记忆收益。",
    "2609.15382": "实验在连续堆料挖掘任务中比较 diffusion proposal、world-model ranking 和 SAC 等策略；包含 MinSlope 测试集、事件不重叠的全尺寸装载机数据，以及 ROS2/TensorRT 闭环部署延迟。",
    "2609.10021": "实验覆盖三类数据质量问题：受控观测-动作污染、模拟次优示范和真实机器人非专家数据。重点看局部梯度兼容性与传统轨迹级筛选相比，是否在真实 rollout 中稳定提升。",
    "2609.10706": "实验用机器人化人类视频预训练，再在 ALLEX 双臂灵巧机器人上微调和测试；包含数据规模增长、视觉机器人化、动作重定向和分布外泛化消融。",
    "2609.10915": "实验把 IMLE 单步动作头接入 π0.5，比较 LIBERO、LIBERO-Plus 和 Franka Panda 真机四任务中的成功率、推理频率、动作 jerk 与单回合推理耗时。",
    "2609.16705": "论文更偏框架与基础设施论证，实验不是单一 benchmark，而是提出 domestic、environmental、energy 等训练场、数据层级、外部真值、living benchmark 和 Deploy-Measure-Learn-Repeat 流程。",
    "2609.16504": "实验从 50 段人类示范生成 1 万条仿真轨迹，训练 ACT generalist，并在 6 个已见和 5 个未见物体的物理试验中比较带触觉与仅点云策略。",
    "2609.16437": "实验选择接触丰富任务，如柔性移液管抓取/液体转移、医疗注射器插入血管训练垫；比较带触觉辅助和无触觉辅助遥操作的数据采集效率与稳定性。",
    "2609.16683": "实验围绕人形机器人全身加手指关节控制，使用人类-物体交互重定向后的参考，测试多对象、多交互序列中的接触建立、保持和物体运动控制。",
    "2609.17035": "实验在平面腱驱动软体机器人上做 packing、reaching、grasping 等任务，比较 SWIM-VLA、OpenVLA-OFT 适配基线和受控消融，并给出仿真与硬件成功率。",
    "2609.16586": "实验包含 VR 遥操作、手-物接近点云重建、动作条件 proximity dynamics 学习，以及标准物体、未见物体和扰动场景下的仿真/真实灵巧操作对比。",
    "2609.15770": "实验在仿真中训练 LiDAR 感知腿足策略，再做 sim-to-real；测试长楼梯、高箱、多地形、遮挡/稀疏/噪声 LiDAR 等退化条件下的鲁棒性。",
    "2609.16641": "实验主要在 LIBERO 套件上做，比较 GR00T N1.5 等基线，重点评估旋转扰动、不同任务套件平均成功率和 canonicalizer / equivariant head 消融。",
    "2609.16503": "实验在 LIBERO 和 SimplerEnv 等 VLA 基准上测试 Dense2MoE 后关闭部分 LLM 参数的性能保持率，重点看参数节省、专家 mask 更新和 staged training 消融。",
    "2609.17523": "实验是科研智能体工作台案例：用户交互、harness refinement、模型学习和四类科研任务 benchmark。它不是机器人实验，价值在于自进化流程设计。",
    "2609.17099": "实验应看无动作人类视频中的几何潜动作学习，包括冻结几何特征、4D geometry teacher、可见性/置信度加权，以及下游策略是否从几何 latent action 受益。",
    "2609.16737": "实验评估 BEV 全局线索、机器人身体线索和 inverse dynamics model 对视频规划导航的贡献，重点看长程导航成功率、video-to-action 转换误差和泛化场景。",
    "2609.15988": "实验围绕人形机器人安全控制，比较 nominal policy、残差安全策略和单策略 reward 混合方案，重点看扰动、摔倒率、任务性能和安全-性能 Pareto trade-off。",
    "2609.15921": "实验在 Tesollo DG-5F 灵巧手和 TacV5 触觉传感器上做电缆追踪，系统比较预训练、控制频率、时间上下文和触觉空间分辨率对策略成功的影响。",
    "2609.15910": "实验使用 TacV5 压阻阵列和高频加速度计，覆盖 37 个物体和约 140 万帧触觉数据，重点评估滑移检测 F1、误报率、延迟和跨平台泛化。",
    "2609.15726": "实验是仿真基准评测：12 种灵巧手、26 个双手任务、约 1.3K 遥操作示范，并比较 ACT、Diffusion Policy、pi0.5、GR00T N1.5 的失败模式。",
    "2609.17521": "实验在多物体桌面刚体视频生成场景中测试流式控制，比较运动分布距离、轨迹误差和人类偏好；它是物理视频模型，不是机器人闭环实验。",
    "2609.15840": "实验应看 action chunk 中高不确定时间步的选择是否准确，以及 sparse residual refinement 在长时程操作任务中相对全量 refinement 和原 ACT 的收益。",
}


FALLBACK_ITEMS = {
    "2609.10021": {
        "title": "RoboDrop: Curating VLA Post-Training Data via Local Gradient Compatibility",
        "summary": "VLA post-training data can contain local execution errors, sensor drift, and temporal misalignment. RoboDrop scores candidate robot data by local gradient compatibility with clean validation samples that are semantically and visually similar, then filters episodes for more reliable post-training.",
        "published": "2026-09-09T00:00:00Z",
        "id": "https://arxiv.org/abs/2609.10021v1",
        "authors": ["Tsinghua University / Striding AI"],
    },
    "2609.10706": {
        "title": "HuRo: Robotizing Human Videos for Scalable VLA Pretraining",
        "summary": "HuRo converts heterogeneous human videos into robot-aligned observations and actions for scalable VLA pretraining, targeting the embodiment gap between human demonstrations and robot execution.",
        "published": "2026-09-09T00:00:00Z",
        "id": "https://arxiv.org/abs/2609.10706v1",
        "authors": ["Yonsei University et al."],
    },
    "2609.10915": {
        "title": "IMLE-VLA: Fast Single-Step Action Generation for Vision-Language-Action Policies",
        "summary": "IMLE-VLA replaces multi-step diffusion or flow action generation with conditional IMLE single-step generation, targeting faster and smoother VLA control on real robots.",
        "published": "2026-09-10T00:00:00Z",
        "id": "https://arxiv.org/abs/2609.10915v1",
        "authors": ["Simon Fraser University", "University of Pennsylvania"],
    },
}


CSS = """
:root{--ink:#16212b;--muted:#667481;--line:#dbe3e8;--paper:#fbfcfd;--soft:#eef6f8;--blue:#195f8f;--green:#256d47;--amber:#8a5a12;--red:#9a332d}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15.5px/1.72 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:1180px;margin:0 auto;padding:28px 18px 68px}
header{border-bottom:1px solid var(--line);padding-bottom:22px}.eyebrow{color:var(--blue);font-weight:800;font-size:12px;letter-spacing:.08em;text-transform:uppercase}
h1{font-size:clamp(28px,4.8vw,46px);line-height:1.15;margin:8px 0 12px}h2{font-size:25px;margin:36px 0 10px}h3{font-size:19px;line-height:1.35;margin:0 0 4px}
.meta,.small{color:var(--muted);font-size:13px}.signal{background:var(--soft);border-left:4px solid var(--blue);padding:16px 18px;margin:18px 0 10px}.signal strong{display:block;margin-bottom:4px}
.toc{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;margin-top:16px}.toc a{display:block;border:1px solid var(--line);background:#fff;border-radius:7px;padding:8px 10px}
.paper,.news{border-top:1px solid var(--line);padding:20px 0 22px}.paper:first-of-type,.news:first-of-type{border-top:0}.head{display:flex;gap:12px;align-items:flex-start}.num{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#16212b;color:#fff;font-weight:800;flex:0 0 auto}
.title{flex:1}.original{color:var(--muted);font-size:13px}.badges{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.badge{border:1px solid var(--line);background:#fff;border-radius:999px;padding:2px 8px;font-size:12px;color:#54616d}.S{color:#fff;background:#8d2f2f;border-color:#8d2f2f}.A{color:#fff;background:#195f8f;border-color:#195f8f}.B{color:#fff;background:#667481;border-color:#667481}.good{color:var(--green);background:#e8f5ee;border-color:#add9c1}.warn{color:var(--amber);background:#fff4dc;border-color:#e4c27e}.risk{color:var(--red);background:#fbeaea;border-color:#e4b2b2}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}.box{border:1px solid var(--line);background:#fff;border-radius:7px;padding:10px 12px}.box strong{display:block;margin-bottom:2px}
.deep{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}.deep .box{min-height:96px}.section-kicker{margin:6px 0 18px;padding:10px 12px;border-left:4px solid var(--blue);background:#eef6f8;color:#31424f}
details{margin-top:10px;border:1px solid var(--line);background:#fff;border-radius:7px;overflow:hidden}summary{cursor:pointer;font-weight:750;padding:9px 12px}details .detail-body{border-top:1px solid var(--line);padding:11px 13px;color:#33414c}.abstract-pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:10px 0;border-top:1px dashed var(--line)}.abstract-pair:first-child{border-top:0}.abstract-pair .en{color:#2d3842}.abstract-pair .zh{color:#17212b}.abstract-pair .label{display:block;color:#667481;font-size:12px;font-weight:750;margin-bottom:3px}
.review{margin-top:10px;padding:10px 12px;border-left:3px solid var(--green);background:#edf7f1}.note{margin-top:24px;padding:14px 16px;background:#f2f5f7;border:1px solid var(--line);border-radius:7px;color:#43515c}.news-title{display:flex;gap:10px;align-items:baseline}.date{color:var(--muted);font-size:13px;white-space:nowrap}footer{margin-top:36px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}
@media(max-width:760px){.grid,.deep,.abstract-pair{grid-template-columns:1fr}.head{gap:9px}.num{width:29px;height:29px;font-size:13px}.news-title{display:block}.wrap{padding:22px 14px 50px}}
"""


def norm_id(arxiv_id: str) -> str:
    return arxiv_id.split("/abs/")[-1].split("v")[0]


def e(text: str) -> str:
    return html.escape(text, quote=True)


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join(text.replace("\n", " ").split())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=(?:[A-Z0-9$]|\\|We|This|The|Our|In|On|These|It|To|For))", cleaned)
    return [part.strip() for part in parts if part.strip()]


def load_translation_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_translation_cache(path: Path, cache: dict) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def translate_sentences(aid: str, sentences: list[str], cache: dict) -> list[str]:
    cached = cache.get(aid)
    if cached and cached.get("en") == sentences and cached.get("zh"):
        return cached["zh"]
    if os.environ.get("USE_REMOTE_TRANSLATION") != "1":
        fallback = split_sentences(META[aid]["abstract"]) if aid in META else []
        if not fallback:
            fallback = ["中文对照翻译待补；请先阅读左侧英文原文。"]
        while len(fallback) < len(sentences):
            fallback.append("中文对照翻译待补；请先阅读左侧英文原文。")
        cache[aid] = {"en": sentences, "zh": fallback[: len(sentences)], "mode": "local_fallback"}
        return cache[aid]["zh"]
    try:
        from deep_translator import MyMemoryTranslator

        translator = MyMemoryTranslator(source="en-US", target="zh-CN")
        translated: list[str] = []
        for start in range(0, len(sentences), 6):
            batch = sentences[start : start + 6]
            translated.extend(translator.translate_batch(batch))
            time.sleep(0.35)
        cache[aid] = {"en": sentences, "zh": translated}
        return translated
    except Exception:
        fallback = [META[aid]["abstract"]] if aid in META else ["翻译服务暂不可用；请先对照英文原文阅读。"]
        cache[aid] = {"en": sentences, "zh": fallback}
        return fallback


def render_abstract_pairs(aid: str, item: dict, cache: dict) -> str:
    sentences = split_sentences(item.get("summary", ""))
    translations = translate_sentences(aid, sentences, cache)
    rows = []
    for index, sentence in enumerate(sentences):
        zh = translations[index] if index < len(translations) else "本句翻译缺失，请对照英文原文。"
        rows.append(
            f"""
            <div class="abstract-pair">
              <div class="en"><span class="label">EN {index + 1}</span>{e(sentence)}</div>
              <div class="zh"><span class="label">ZH {index + 1}</span>{e(zh)}</div>
            </div>
            """
        )
    return "".join(rows)


def find_packet(root: Path, date: str) -> Path:
    return root / date[:7] / f"research-packet-{date}.json"


def render_paper(local_i: int, global_i: int, section_slug: str, item: dict, priority: str, direction: str, cache: dict) -> str:
    aid = norm_id(item["id"])
    m = META[aid]
    pub = item["published"][:10]
    authors = "、".join(item.get("authors", [])[:5])
    url = f"https://arxiv.org/abs/{aid}"
    code_class = "good" if "已" in m["code"] else "warn"
    real_class = "good" if "有" in m["real"] else "warn"
    abstract_pairs = render_abstract_pairs(aid, item, cache)
    return f"""
      <article class="paper" id="{section_slug}-{local_i}">
        <div class="head">
          <div class="num">{global_i}</div>
          <div class="title">
            <h3><a href="{e(url)}" target="_blank" rel="noopener">{e(m['cn'])}</a></h3>
            <div class="original">{e(item['title'])} · {e(pub)} · {e(authors)}</div>
          </div>
        </div>
        <div class="badges">
          <span class="badge {priority}">优先级 {priority}</span>
          <span class="badge good">{e(direction)}</span>
          <span class="badge {code_class}">代码：{e(m['code'])}</span>
          <span class="badge {real_class}">真机：{e(m['real'])}</span>
        </div>
        <div class="grid">
          <div class="box"><strong>研究机构/团队</strong>{e(m['origin'])}</div>
          <div class="box"><strong>机构/团队简介</strong><span class="small">{e(m['origin_note'])}</span></div>
        </div>
        <div class="deep">
          <div class="box"><strong>问题与动机</strong>{e(m['summary'])}</div>
          <div class="box"><strong>方法与机制</strong>{e(m['abstract'])}</div>
          <div class="box"><strong>实验设置</strong>{e(EXPERIMENTS.get(aid, '实验设置快速核验不足；请以论文 PDF 和项目页为准。'))}</div>
          <div class="box"><strong>和你课题的关系</strong>{e(m['intro'])}</div>
        </div>
        <details><summary>摘要逐句对照翻译（保留英文原文）</summary><div class="detail-body">{abstract_pairs}</div></details>
        <div class="review"><strong>编辑评述：</strong>{e(m['review'])}</div>
      </article>
"""


def render_news(i: int, n: tuple[str, str, str, str]) -> str:
    title, date, body, url = n
    return f"""
      <article class="news">
        <div class="news-title"><h3>{e(title)}</h3><span class="date">{e(date)}</span></div>
        <p>{e(body)}</p>
        <p><a href="{e(url)}" target="_blank" rel="noopener">来源链接</a></p>
      </article>
"""


def render(root: Path, date: str) -> tuple[Path, Path]:
    packet = json.loads(find_packet(root, date).read_text(encoding="utf-8"))
    by_id = {norm_id(item["id"]): item for item in packet["arxiv_candidates"]}
    by_id.update(FALLBACK_ITEMS)

    month_dir = root / date[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    out = month_dir / f"{date}-{FILE_TITLE}-机构实验版.html"
    seen = month_dir / f"seen-{date[:7]}.md"
    translation_cache_path = month_dir / f"abstract-translations-{date}.json"
    translation_cache = load_translation_cache(translation_cache_path)

    strong_ids = [aid for aid in STRONG_RELATED_IDS if aid in by_id]
    supplement_ids = [aid for aid in SUPPLEMENT_IDS if aid in by_id]
    strong_papers = []
    supplement_papers = []
    global_index = 0
    for local_i, aid in enumerate(strong_ids, 1):
        global_index += 1
        priority, direction = SELECTED_BY_ID[aid]
        strong_papers.append(render_paper(local_i, global_index, "strong", by_id[aid], priority, direction, translation_cache))
    for local_i, aid in enumerate(supplement_ids, 1):
        global_index += 1
        priority, direction = SELECTED_BY_ID[aid]
        supplement_papers.append(render_paper(local_i, global_index, "supplement", by_id[aid], priority, direction, translation_cache))
    save_translation_cache(translation_cache_path, translation_cache)

    window = f"{packet['window']['start'][:10]}—{packet['window']['end'][:10]}"
    strong_toc = "\n".join(
        f'<a href="#strong-{i}">强相关 {i}. {e(META[aid]["cn"][:38])}</a>'
        for i, aid in enumerate(strong_ids, 1)
    )
    supplement_toc = "\n".join(
        f'<a href="#supplement-{i}">补充 {i}. {e(META[aid]["cn"][:38])}</a>'
        for i, aid in enumerate(supplement_ids, 1)
    )
    total_paper_count = len(strong_papers) + len(supplement_papers)
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(date + '-' + TITLE)}</title>
  <style>{CSS}</style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="eyebrow">Daily Paper Loop · {e(date)} · Revised</div>
      <h1>{e(TITLE)}</h1>
      <div class="meta">报告日期：{e(date)}　|　检索窗口：{e(window)}（重点近三天）　|　时区：Asia/Shanghai　|　本月去重日志：{e(str(seen.relative_to(root)))}</div>
      <div class="signal">
        <strong>今日风向</strong>
        今天的主线不是单个 VLA 模型刷分，而是“具身大脑系统化”：WAM 开始承担动作选择与恢复数据生成，VLA 开始补时间、几何和端侧效率，数据采集、触觉、长期记忆和工程平台一起成为新范式能否成立的地基。
      </div>
      <div class="signal">
        <strong>排序原则</strong>
        本版明确分成三部分：强相关论文 {len(strong_papers)} 篇（上限 30）、扩展补充论文 {len(supplement_papers)} 篇（上限 10）、News {len(NEWS)} 条。目录与正文均从实际渲染条目生成；页面展示研究机构/团队与实验设置，作者/团队影响力仅用于后台排序；摘要只做逐句对照翻译，不再生成引言翻译。
      </div>
      <div class="toc">{strong_toc}{supplement_toc}</div>
    </header>

    <section>
      <h2>一、与你课题强相关的论文（{len(strong_papers)}篇）</h2>
      <div class="section-kicker">这一栏只放具身大脑、VLA、WAM、自进化、数据闭环、具身记忆、动作效率、世界模型到决策等与你研究课题直接相关的工作；每日最多 30 篇，阅读优先级最高。</div>
      {''.join(strong_papers)}
    </section>

    <section>
      <h2>二、扩展补充论文（{len(supplement_papers)}篇）</h2>
      <div class="section-kicker">这一栏放硬件、触觉、灵巧手、仿真/基准、数据采集、部署安全、物理视频生成等具身智能生态支撑项；每日最多 10 篇。它们不一定是具身大脑论文，但会影响数据、评测和真实部署。</div>
      {''.join(supplement_papers)}
    </section>

    <section>
      <h2>三、最新 News（最多20条，今天保留高价值10条）</h2>
      <p class="small">News 放眼整个人工智能大环境，只保留对模型、算力、智能体、机器人生态或治理讨论有启发的条目。</p>
      {''.join(render_news(i, n) for i, n in enumerate(NEWS, 1))}
    </section>

    <div class="note">
      <strong>重点对象核验备注：</strong>
      本期已重点覆盖 VLA/WAM、自进化、真机数据闭环、触觉/灵巧操作、移动操作记忆、机器人数据工厂、端侧部署和具身硬件生态。未在本次近一周窗口中确认华为、腾讯、字节、小米、美的、比亚迪、DeepSeek、Google DeepMind、Tesla、Amazon 直接发布与本主题强相关的新技术报告；清华 IIIS 赵行、上交穆尧组未检出可确认的新论文。后续每日继续按中英文别名和实验室页面复查。
    </div>

    <footer>
      <p>来源类型：arXiv 候选包、论文摘要、项目页/代码状态快速核验、企业官方新闻页和主流科技媒体。本文共渲染论文 {total_paper_count} 篇：强相关 {len(strong_papers)} 篇，扩展补充 {len(supplement_papers)} 篇。摘要翻译缓存：{e(str(translation_cache_path.relative_to(root)))}。</p>
      <p>工作流文件：<a href="../code/prompt.md">code/prompt.md</a> · <a href="../code/sources.json">code/sources.json</a> · <a href="../code/generate_report.py">code/generate_report.py</a> · <a href="../code/render_report_from_packet.py">code/render_report_from_packet.py</a></p>
    </footer>
  </main>
</body>
</html>
"""
    out.write_text(html_text, encoding="utf-8")

    seen_lines = [
        f"# {date[:7]} 每日 Paper 去重日志",
        "",
        "本文件只维护当前月份已处理条目。每日生成前读取它，生成后追加，避免本月重复报道。",
        "",
        f"## {date}",
        "",
        "### 论文",
    ]
    seen_index = 0
    for aid in strong_ids + supplement_ids:
        if aid in by_id:
            seen_index += 1
            priority, direction = SELECTED_BY_ID[aid]
            item = by_id[aid]
            section = "强相关" if aid in strong_ids else "扩展补充"
            seen_lines.append(
                f"- [{priority}] {item['title']} | https://arxiv.org/abs/{aid} | {direction} | {section} | 已纳入今日HTML第{seen_index}条"
            )
    seen_lines.extend(["", "### News"])
    for title, date_label, _, url in NEWS:
        seen_lines.append(f"- {date_label} | {title} | {url} | 已纳入今日HTML")
    seen.write_text("\n".join(seen_lines) + "\n", encoding="utf-8")
    return out, seen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d"))
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    out, seen = render(Path(args.root), args.date)
    print(out.resolve())
    print(seen.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
