# 迷你模拟消费者调研平台

AI 驱动的消费者调研工具，内置 5 个固定人设，支持 Mock 和真实 AI 双模式。

## 5 个消费者人设

| 人设 | 年龄 | 城市 | 职业 | 收入 | 标签 |
|------|------|------|------|------|------|
| 小琳 | 28岁 | 杭州 | 互联网运营 | ¥8k | 成分党、国货+日韩、理性种草 |
| 大刘 | 35岁 | 深圳 | 产品经理 | ¥25k | 数码控、新能源车主、户外露营 |
| 张姨 | 52岁 | 洛阳 | 退休教师 | ¥5k | 养生达人、广场舞、比价能手 |
| 阿杰 | 22岁 | 上海 | 初级程序员 | ¥6k | 外卖达人、手游月卡党、B站用户 |
| Lily | 30岁 | 成都 | 市场经理 | ¥18k | CrossFit、猫奴、轻奢包控 |

## 快速开始

### 方式一：Flask 后端（推荐）

```bash
pip install -r requirements.txt
python app.py
# 访问 http://127.0.0.1:5000
```

Mock 模式开箱即用。如需真实 AI：

```bash
# Windows
set ANTHROPIC_API_KEY=sk-ant-xxx && python app.py

# Mac / Linux
export ANTHROPIC_API_KEY=sk-ant-xxx && python app.py
```

### 方式二：纯前端版

直接在浏览器打开 `standalone.html`。页面顶部可填入 API Key 切换为 AI 模式，也可配合 `proxy.js` 使用。

### 方式三：API 代理

`proxy.js` 支持多后端自动检测：

```bash
node proxy.js
```

优先级：ANTHROPIC_API_KEY → DEEPSEEK_API_KEY → Ollama 本地模型。

## 功能

- 5 个固定消费者人设，一键切换
- 5 种暖色调主题（暖杏、蜜桃、燕麦、琥珀、玫瑰）
- Mock 关键词匹配回答 + 情感自动分类
- What-If 场景测试卡
- 对话线程 + Smart Follow-up 追问
- 情感追踪条（种草/中立/吐槽）
