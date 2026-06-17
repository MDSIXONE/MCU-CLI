# MCU-CLI 规范符合性审查报告

> 审查基准：[HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) 的 `HARNESS.md` 方法论与 5 大设计原则
> 审查日期：2026-06-17
> 审查对象：MCU-CLI 当前仓库状态

## 一、审查结论

| 级别 | 项数 | 说明 |
|------|------|------|
| 符合 | 6 | 文档、许可证、真实集成、自描述、输出验证、SKILL.md |
| 部分符合 | 2 | CLI 框架（argparse 非 Click）、JSON 输出（无全局 flag） |
| 不符合 | 6 | 打包分发、包结构、打包配置、REPL 双模式、测试体系、Python 版本声明 |

**总评**：MCU-CLI 在「真实软件集成」与「文档完整性」上达标，但距 CLI-Anything 规范的「`pip install -e .` 即用 + Agent 原生 CLI + 生产级测试」标准存在**结构性差距**。核心问题集中在四大基础设施：**打包/分发、包结构、Agent 原生设计、测试体系**。若要作为开源项目让他人直接部署并达到 CLI-Anything 规范水准，需补齐 P0 级差距。

---

## 二、不符合项详解与改进方案

### P0-1 无可安装的打包入口（打包分发）

**CLI-Anything 规范**：每个 CLI 通过 `pip install -e .` 安装到 PATH，安装后可直接 `cli-anything-<software> --help`，无需 `python path/to/cli.py`。

**MCU-CLI 现状**：
- `mcucli/setup.py` 是 Gary Dev Agent 的环境安装脚本（2000+ 行），**明确阻止 `pip install`**（第 28-46 行拦截 setuptools 命令）
- 无 `console_scripts` / `entry_points` 定义
- 用户必须 `python mcucli/mcucli.py <command>` 运行，clone 后无法一行命令安装

**改进方案**：
1. 将 `mcucli/setup.py` 重命名为 `mcucli/gary_setup.py`（或移出仓库），消除"setup.py 却不能 pip install"的误导
2. 新建 `pyproject.toml`（PEP 621 标准），定义 `console_scripts`：
   ```toml
   [project.scripts]
   mcucli = "mcucli.mcucli:main"
   ```
3. 部署方式改为 `pip install -e .`，安装后 `mcucli serial list` 直接可用

---

### P0-2 mcucli/ 不是 Python 包（包结构）

**CLI-Anything 规范**：`cli_anything/<software>/` 含 `__init__.py`，是可导入的 Python 包，`from cli_anything.<software> import ...` 可工作。

**MCU-CLI 现状**：`mcucli/` 目录无 `__init__.py`，不是 Python 包。`mcucli.py` 内部用 `sys.path.insert(0, ...)` + 相对导入 hack（第 9-10 行），无法被外部 `import mcucli`。

**改进方案**：
1. 新建 `mcucli/__init__.py`（暴露 `main` 等公共 API）
2. 将 `scripts/`、`hardware/`、`compiler/` 的导入从 `from scripts.flash_tool import ...` 改为 `from mcucli.scripts.flash_tool import ...`
3. 移除 `mcucli.py` 中的 `sys.path.insert` hack

---

### P0-3 无 pyproject.toml / 打包配置（打包配置）

**CLI-Anything 规范**：`setup.py`（setuptools）或 `pyproject.toml`，含 `python_requires`、`dependencies`、`console_scripts`。

**MCU-CLI 现状**：
- 无 `pyproject.toml`
- `mcucli/setup.py` 非打包脚本
- `requirements.txt` 无版本约束（`pyocd`、`pyserial` 裸写）

**改进方案**：新建 `pyproject.toml`：
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "mcucli"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pyocd>=0.35",
    "pyserial>=3.5",
]

[project.optional-dependencies]
uart = ["stm32loader>=0.5"]
esp32 = ["adafruit-ampy>=1.1"]

[project.scripts]
mcucli = "mcucli.mcucli:main"

[tool.setuptools.packages.find]
include = ["mcucli*"]
```

---

### P0-4 未声明 Python 版本（Python 版本）

**CLI-Anything 规范**：声明 `python_requires`（≥3.10），依赖版本锁定。

**MCU-CLI 现状**：无 `python_requires`，`requirements.txt` 无版本号，部署者无法预知兼容性。

**改进方案**：随 P0-3 的 `pyproject.toml` 一并声明 `requires-python = ">=3.10"`，依赖加版本下限。

---

### P1-1 无 --json 全局标志（Agent 原生设计）

**CLI-Anything 规范**：每条命令内置 `--json` 标志，`cli --json <command>` 输出结构化 JSON 供 Agent 消费；无 `--json` 时输出人类可读表格。Agent 通过 `--help` 和 `which` 发现能力。

**MCU-CLI 现状**：部分命令（flash/connect）用 `json.dumps` 输出，但：
- 无全局 `--json` flag
- 人类可读输出与机器输出未分离（如 `serial list` 可能直接 print 列表）
- Agent 无法控制输出格式

**改进方案**：
1. 主 parser 加 `--json` 全局 flag
2. 各命令根据 `--json` 决定输出 JSON 还是人类可读格式
3. 统一 JSON 输出 schema（`{success, data, error, message}`）

---

### P1-2 无测试体系（测试）

**CLI-Anything 规范**：四层测试，100% 覆盖：
- 单元测试（`test_core.py`）— 隔离测试核心函数
- E2E native（项目文件生成管道）
- E2E true backend（真实软件调用 + 输出验证）
- CLI subprocess（`subprocess.run` 验证已安装命令）
- `pytest.ini` 配置，`python -m pytest` 一键运行

**MCU-CLI 现状**：**零测试**——无 `tests/` 目录、无 `pytest.ini`、无 `conftest.py`。

**改进方案**：
1. 新建 `tests/` 目录 + `pytest.ini`
2. 优先补单元测试（覆盖 `flash_mspm0` 命令构造、`resolve_jlink_path` 解析、`list_jlink_probes` 枚举、config 常量）
3. 补 CLI subprocess 测试（`mcucli flash mspm0 --dry-run` → 校验输出 JSON）
4. E2E true backend 测试用 `--dry-run` 模式规避硬件依赖，真实烧录测试标记 `@pytest.mark.hardware` 按需运行

---

### P2-1 无 REPL 交互模式（双模式交互）

**CLI-Anything 规范**：裸命令（无子命令）进入有状态 REPL，含品牌横幅、上下文提示符、命令历史；带子命令走脚本模式。

**MCU-CLI 现状**：仅子命令模式，裸运行 `python mcucli.py` 无子命令时直接报错退出。

**改进方案**（可选，优先级低）：
1. 用 Python `cmd` 模块实现 REPL
2. 裸命令进入 REPL，保留当前项目上下文（如已 connect 的芯片）
3. 复用 CLI-Anything 的 `repl_skin.py` 统一界面思路

---

### P2-2 CLI 框架为 argparse 非 Click（CLI 框架）

**CLI-Anything 规范**：统一用 [Click](https://click.palletsprojects.com/) 8.0+，Group+Command 模式，便于自动生成 SKILL.md 和统一 REPL。

**MCU-CLI 现状**：argparse 手写 subparsers。

**改进说明**：argparse 是标准库，功能上能满足需求，**非必须迁移**。CLI-Anything 选 Click 主要为自动生成 SKILL.md（从装饰器提取元数据）。若不追求自动化生成 SKILL.md，保留 argparse 可接受，但需补齐 `--json`、REPL、测试等其余规范项。若要完全对标，可逐步迁移到 Click。

---

## 三、部分符合项

| 项 | 现状 | 差距 | 改进 |
|----|------|------|------|
| CLI 框架 | argparse 实现完整子命令分组 | 非 Click，无法自动生成 SKILL.md | 保留 argparse 或迁移 Click（见 P2-2） |
| JSON 输出 | flash/connect 用 json.dumps | 无全局 --json，人类/机器输出未分离 | 加 --json flag（见 P1-1） |

---

## 四、符合项确认

以下 6 项已达标，无需改动：

1. **SKILL.md 规范** — `.agent/skills/mcucli/SKILL.md` 有 YAML frontmatter（`name` + `description`）+ 命令文档 + 使用示例，符合 CLI-Anything 的技能发现协议
2. **LICENSE** — `LICENSE` 文件为 Apache-2.0 全文，与 CLI-Anything 一致
3. **真实软件集成** — 调用真实 J-Link Commander / pyOCD / stm32loader，不替代后端，符合「零妥协依赖」原则
4. **自描述** — argparse 自带 `--help`，各子命令有 help 文本，Agent 可经 `--help` 发现能力
5. **输出验证** — `flash_mspm0` 校验 `Downloading file` + `O.K.` + PC 寄存器，不只信退出码，符合 HARNESS.md「输出验证」经验
6. **README** — 含部署步骤、命令参考、目录结构、许可证，符合开源文档规范

---

## 五、改进优先级与路线图

### P0（必须，阻塞开源部署）

- [ ] 重命名/移除误导性 `mcucli/setup.py`
- [ ] 新建 `pyproject.toml`（含 `python_requires`、`dependencies`、`console_scripts`）
- [ ] 新建 `mcucli/__init__.py`，修复包导入路径
- [ ] 验证 `pip install -e .` 后 `mcucli --help` 可用

### P1（重要，Agent 原生与质量保障）

- [ ] 加全局 `--json` flag，统一机器输出 schema
- [ ] 建 `tests/` + `pytest.ini`，补单元测试与 CLI subprocess 测试
- [ ] `requirements.txt` 加版本下限

### P2（可选，完整对标）

- [ ] 迁移 Click 框架（或保留 argparse 并记录为有意决策）
- [ ] 实现 REPL 交互模式
- [ ] 补 E2E true backend 测试（标记 `@pytest.mark.hardware`）

---

## 六、与 CLI-Anything 定位的差异说明

CLI-Anything 的定位是「为任意**桌面软件**（GIMP/Blender/LibreOffice）生成 Agent 原生 CLI」，其规范偏重软件封装为 CLI + 项目文件生成 + 真实后端渲染。

MCU-CLI 是**嵌入式开发工具集**，定位略有不同：
- 不生成项目文件，而是操作硬件（烧录/串口/调试）
- 后端是硬件探针 + 外部工具链，非桌面应用

因此，**「真实软件集成」「输出验证」「零妥协依赖」** 等原则 MCU-CLI 已天然符合；而**「双模式 REPL」「--json 全局」「四层测试」** 等基础设施规范是通用 CLI 最佳实践，MCU-CLI 应补齐。**「Click 框架」** 属 CLI-Anything 的技术选型，MCU-CLI 保留 argparse 可作为有意决策记录，但其余规范项建议尽量对齐以提升开源可部署性。

---

*本报告由对照 CLI-Anything 仓库（2026-06-17 状态）审查生成。*
