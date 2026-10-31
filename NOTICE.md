# 来源与作者说明

本工作台为独立实现的本地研究应用，不是 AlphaGen 官方产品。未分发上游 AlphaGen 源码、模型权重、Kronos 源码或模型权重。

仓库维护者 / Repository maintainer: [Liu123215](https://github.com/Liu123215)。本仓库没有附带开源许可证；不应将此页面或上游项目的许可证理解为自动授予本工作台的复制、修改或再分发许可。

## AlphaGen 上游研究

- 仓库：https://github.com/ICT-FinD-Lab/alphagen
- 维护团队：MLDM research group, IIP, ICT, CAS；上游列出的维护者包括 Hongyan Xue、Shuo Yu。
- Shuo Yu, Hongyan Xue, Xiang Ao, Feiyang Pan, Jia He, Dandan Tu, Qing He. **Generating Synergistic Formulaic Alpha Collections via Reinforcement Learning**. KDD 2023. DOI: https://doi.org/10.1145/3580305.3599831
- 本应用支持其 `LinearAlphaPool.to_json_dict()` 的 `exprs` / `weights` 数据结构，并独立实现了部分算子解释与研究界面。兼容格式不代表数值与上游逐位一致，也不代表上游授权其代码再分发。
- 上游研究和源码权利归其各自权利人。本项目未为上游代码另行指定许可证；截至 2026-10-31，GitHub 仓库元数据未显示可识别的许可证，这不构成对全部文件权利状况的法律判断。如后续合并或分发上游代码，应核实所用提交及有关文件的授权条款。

## 界面参考

按用户要求，工作台的侧栏、深浅主题、参数面板、行情图表和历史明细交互参考用户已有的 Kronos Windows 工作台：https://github.com/Liu123215/kronos-stock-forecast-windows 。未复制其源文件。

该参考项目包含来自 [shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos) 的 MIT 许可模型核心，其原版权声明为 **Copyright (c) 2025 ShiYu**；参见参考项目的 [NOTICE](https://github.com/Liu123215/kronos-stock-forecast-windows/blob/main/NOTICE.md) 与 [LICENSE](https://github.com/Liu123215/kronos-stock-forecast-windows/blob/main/LICENSE)。本工作台不包含 Kronos 模型代码或权重，参考项目的 MIT 许可证不会因此自动成为本工作台的许可证。

## 数据

- 默认演示数据使用固定随机种子独立合成，不是真实证券行情；公司名称与代码只用于示范操作。
- 在线获取从腾讯公开行情网页接口读取前复权日线；数据归相应权利方所有。接口可变更或限流；无实时性与连续性保证。应用不提供数据再分发授权。
- 用户导入的数据及因子池的权利和训练来源由用户确认。

## 依赖

NumPy（BSD-3-Clause）和 pandas（BSD-3-Clause）由各自原作者维护，安装时使用其原始包及许可证。本工作台不打包这些依赖的二进制分发。图表和图标使用本地 SVG，无远程字体、CDN 或跟踪脚本。

## English summary

This workbench is independently implemented and is not an official AlphaGen or Kronos product. It does not bundle either project's source code or model weights. The workbench repository is maintained by [Liu123215](https://github.com/Liu123215); no open-source license is currently included for this repository.

AlphaGen's research, **Generating Synergistic Formulaic Alpha Collections via Reinforcement Learning** (KDD 2023), is by Shuo Yu, Hongyan Xue, Xiang Ao, Feiyang Pan, Jia He, Dandan Tu and Qing He. The [upstream project](https://github.com/ICT-FinD-Lab/alphagen) is maintained by the MLDM research group, IIP, ICT, CAS. Its GitHub repository metadata reported no recognized license on 2026-10-31; review the rights of the exact upstream version before reusing or distributing its code.

The interface was inspired by the [Kronos Windows workbench](https://github.com/Liu123215/kronos-stock-forecast-windows), without copying its source files. That reference includes MIT-licensed Kronos core code with the original notice **Copyright (c) 2025 ShiYu**. Its license applies to the relevant reference materials and does not automatically license this workbench. Market data, user-provided data and dependencies remain subject to their respective owners' rights and licenses.
