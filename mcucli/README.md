# MCU CLI

嵌入式开发工具集，支持 STM32、ESP32、RP2040 等芯片的烧录、串口监控、编译和调试。

## AI 使用指南

**首先加载技能：**
```python
skill("mcucli")
```

加载后即可使用所有硬件操作工具。

## 快速开始

### 1. 列出串口
```bash
python mcucli.py serial list
```

### 2. 重置 MicroPython REPL（重要！）
```bash
python mcucli.py serial reset COM9
```

### 3. 发送命令
```bash
python mcucli.py serial send COM9 "print('Hello')"
```

### 4. 监控串口
```bash
python mcucli.py serial monitor COM9 --duration 10
```

## 任务管理

所有任务存放在 `Project/` 目录下，每个任务包含 `TASK.md` 文档。

**查看任务：**
```bash
ls Project/
cat Project/ESP32_S3LED/TASK.md
```

**创建新任务：**
1. 在 `Project/` 下创建文件夹（格式：`芯片_功能`）
2. 复制 `TASK_TEMPLATE.md` 为 `TASK.md`
3. 填写任务详情

## 支持的芯片

- **STM32**: F0/F1/F3/F4 系列
- **ESP32**: ESP32/S2/S3/C3
- **RP2040**: Pico/Pico W

## 目录结构

```
├── .agent/skills/mcucli/  # 技能文件
├── mcucli/                # 主项目
│   ├── mcucli.py          # 入口
│   ├── scripts/           # 工具脚本
│   ├── hardware/          # 硬件模块
│   └── compiler/          # 编译模块
└── Project/               # 任务目录
    ├── README.md          # 任务管理说明
    ├── TASK_TEMPLATE.md   # 任务模板
    └── ESP32_S3LED/       # 示例任务
        └── TASK.md
```

## 工具列表

| 工具 | 命令 | 功能 |
|------|------|------|
| 串口列表 | `serial list` | 列出所有串口 |
| 串口读取 | `serial read <port>` | 读取串口数据 |
| 串口监控 | `serial monitor <port>` | 持续监控输出 |
| 串口发送 | `serial send <port> <data>` | 发送数据 |
| REPL重置 | `serial reset <port>` | 重置MicroPython |
| SWD烧录 | `flash swd <file>` | SWD烧录固件 |
| UART烧录 | `flash uart <file>` | UART ISP烧录 |
| 编译STM32 | `compile stm32 <file>` | 编译STM32代码 |
| 编译ESP32 | `compile esp32 <file>` | 验证ESP32代码 |
| 工具链检查 | `compile check` | 检查编译工具 |
| 连接设备 | `connect` | SWD连接 |
| 读寄存器 | `regs read` | 读取寄存器 |
| 写寄存器 | `regs write <name> <value>` | 写入寄存器 |
| 复位设备 | `reset` | 复位MCU |

## 依赖

```bash
pip install pyserial pyocd
```

## 许可证

Apache-2.0