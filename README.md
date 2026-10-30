# anime-to-real

把动漫、二次元角色图转成真人照片的 Agent Skill：真人质感，五官带 BJD 娃娃般的精致感，构图固定为头肩特写。适用于 Claude Code、Codex 等支持 skills 的 AI 编程助手。

An agent skill that turns anime / ACG character art into a realistic head-and-shoulders portrait photo.

## 流程

```
原图 ─(Q 版或全身图才做)→ 重画成正常比例的头肩特写漫画
     → 看图写画面描述和必须保留的角色特征
     → 套用提示词模板
     → 参考原图出成片（可选：先生成深度图辅助锁构图，默认关闭）
     → 交付"原图 / 成片"对比拼图和成片文件
```

这套流程来自一个 RunningHub 的 ComfyUI 工作流（Qwen-Image-Edit + 真人化 LoRA + 深度 ControlNet）：
- LoRA 改成了结构化提示词；
- ControlNet 改成可选的"提示词生成深度图"；
- 原工作流依赖本地显卡和私有 LoRA，这里改成了直接调用通用生图模型。

## 出图方式

1. **默认**：使用宿主自带的图像生成工具，例如 Codex 的 imagegen。它需要支持输入参考图。
2. **宿主没有生图工具时**，通过 [OpenLux](https://api.openlux.ai) 调用 image2.5（`gpt-image-2.5-sunburst`）：
   - 环境里装有 openlux-image skill 时，直接使用它的调用脚本；
   - 否则使用本仓库的 `scripts/convert.py`，需要设置环境变量 `OPENLUX_API_KEY`，或在 skill 目录下放一个 `openlux_key.txt`（已被 `.gitignore` 忽略）。

## 安装

把整个仓库放进对应工具的 skills 目录，文件夹名保持 `anime-to-real`：

- **Claude Code**：
  - 全局使用：`~/.claude/skills/anime-to-real/`
  - 只在某个项目里使用：`<项目>/.claude/skills/anime-to-real/`
- **Codex 等其他工具**：放到该工具的 skills 目录。

```bash
git clone https://github.com/mariozhaofan-pixel/anime-to-real ~/.claude/skills/anime-to-real
```

脚本需要 Python 3 和 Pillow（`pip install pillow`）。

## 目录

```
SKILL.md                    流程说明（Agent 读取的主文件）
templates/prep_closeup.md   Q 版或全身图 → 头肩特写漫画
templates/body_real.md      成片（真人化）提示词模板
templates/depth.md          深度图提示词模板（可选）
templates/head_depth.txt    带深度图时加在提示词开头的说明
references/examples.md      实测通过的填写示例
scripts/convert.py          OpenLux 调用脚本：预处理、出图、深度图、拼图
scripts/make_reel.py        原图 / 成片对比拼图
```

## 用法示例

对 Agent 说：

> 把这张动漫角色图转成真人 `D:\images\char.png`

Agent 会按 `SKILL.md` 的流程：看图、写提示词、出图，最后交付对比拼图和成片。

## 许可证

[MIT](LICENSE)
