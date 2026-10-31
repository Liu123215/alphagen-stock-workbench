# 来源与作者说明

本工作台为独立实现的本地研究应用，不是 AlphaGen 官方产品。未分发上游 AlphaGen 源码、模型权重、Kronos 源码或模型权重。

## AlphaGen 上游研究

- 仓库：https://github.com/ICT-FinD-Lab/alphagen
- 维护团队：MLDM research group, IIP, ICT, CAS；上游列出的维护者包括 Hongyan Xue、Shuo Yu。
- Shuo Yu, Hongyan Xue, Xiang Ao, Feiyang Pan, Jia He, Dandan Tu, Qing He. **Generating Synergistic Formulaic Alpha Collections via Reinforcement Learning**. KDD 2023. DOI: https://doi.org/10.1145/3580305.3599831
- 本应用支持其 `LinearAlphaPool.to_json_dict()` 的 `exprs` / `weights` 数据结构，并独立实现了部分算子解释与研究界面。兼容格式不代表数值与上游逐位一致，也不代表上游授权其代码再分发。
- 上游权利归原作者；本项目未为上游代码另行指定许可证。如后续合并或分发上游代码，应核实所用提交的授权条款。

## 界面参考

按用户要求，工作台的侧栏、深浅主题、参数面板、行情图表和历史明细交互参考用户已有的 Kronos Windows 工作台：https://github.com/Liu123215/kronos-stock-forecast-windows 。未复制其源文件。

## 数据

- 默认演示数据使用固定随机种子独立合成，不是真实证券行情；公司名称与代码只用于示范操作。
- 在线获取从腾讯公开行情网页接口读取前复权日线；数据归相应权利方所有。接口可变更或限流；无实时性与连续性保证。应用不提供数据再分发授权。
- 用户导入的数据及因子池的权利和训练来源由用户确认。

## 依赖

NumPy（BSD-3-Clause）和 pandas（BSD-3-Clause）由各自原作者维护，安装时使用其原始包及许可证。本工作台不打包这些依赖的二进制分发。图表和图标使用本地 SVG，无远程字体、CDN 或跟踪脚本。
