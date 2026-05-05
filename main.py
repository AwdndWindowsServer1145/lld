import aiohttp
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.api.message_components import *
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from astrbot.core.utils.astrbot_path import get_astrbot_data_path


@register(
    "international_situation",
    "斯基瓦德·杨",
    "AI驱动的国际形势分析插件，支持智能分析、深度报告、地区对比和可视化输出",
    "3.0.0",
)
class InternationalSituationPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.deepseek_api_key = config.get("deepseek_api_key", "sk-79815c1de1304dc08366cda3df6b6733")
        self.deepseek_base_url = "https://api.deepseek.com/v1/chat/completions"
        self.temperature = config.get("ai_temperature", 0.5)
        self.max_tokens = config.get("max_tokens", 2000)
        
        # 初始化存储路径
        self.data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        self.data_path.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """插件初始化"""
        logger.info("国际形势分析插件 v3.0 已加载")
        status = '已配置' if self.deepseek_api_key else '未配置'
        logger.info(f"DeepSeek API 配置状态: {status}")
        
    async def _call_deepseek(self, prompt: str, system_prompt: str = None, temperature: float = None, max_tokens: int = None) -> str:
        """调用 DeepSeek API"""
        if not self.deepseek_api_key:
            return "错误：未配置 DeepSeek API Key"
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.deepseek_base_url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await resp.text()
                        logger.error(f"DeepSeek API 错误 {resp.status}: {error_text}")
                        return f"API 调用失败 ({resp.status})"
        except aiohttp.ClientError as e:
            logger.error(f"网络错误: {e}")
            return f"网络错误: {str(e)}"
        except Exception as e:
            logger.error(f"调用失败: {e}")
            return f"调用失败: {str(e)}"
    
    def _get_timestamp(self) -> str:
        """获取格式化的时间戳"""
        return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    
    # ==================== 基础指令 ====================
    
    @filter.command("situation", alias={"形势", "国际形势"})
    async def get_situation(self, event: AstrMessageEvent):
        """获取当前国际形势摘要"""
        yield event.plain_result("🤖 正在使用 AI 分析国际形势，请稍候...")
        
        system_prompt = """你是一位资深的国际关系分析师，专注于全球政治、经济、军事和外交事务。
请基于你的最新知识，提供当前国际形势的简明摘要。

要求：
1. 涵盖主要地区：中东、东欧、亚太、美洲、欧洲、非洲
2. 突出重要事件和动向
3. 分析关键国家外交动态
4. 提及全球经济和贸易形势
5. 使用专业但易懂的语言
6. 控制在600字以内
7. 使用数字序号或项目符号分点列出"""

        prompt = "请分析2026年5月的国际形势，提供最新动态摘要。包括地缘政治、经济、军事等方面。"
        
        response = await self._call_deepseek(prompt, system_prompt, temperature=0.5)
        
        if response and not response.startswith("错误") and not response.startswith("API"):
            timestamp = self._get_timestamp()
            result = f"""🌍 国际形势 AI 分析
📅 {timestamp}

{response}

💡 提示：
• /situation_detail - 深度分析报告
• /region <地区> - 地区形势分析
• /compare <国1> <国2> - 国家对比
• /hotspot - 国际热点
• /situation_help - 查看所有指令"""
            yield event.plain_result(result)
        else:
            yield event.plain_result(f"❌ {response or '获取分析失败，请稍后重试'}")
    
    @filter.command("situation_detail", alias={"深度分析", "detail"})
    async def get_detailed_analysis(self, event: AstrMessageEvent):
        """获取深度国际形势分析"""
        yield event.plain_result("📊 正在生成深度分析报告，这可能需要30-60秒...")
        
        system_prompt = """你是一位顶级的国际战略分析师，擅长深度分析和趋势预测。
请撰写一份专业的国际形势深度分析报告。

报告结构：
1. **全球战略格局**
   - 大国关系现状
   - 地缘政治新变化
   - 国际秩序演变

2. **区域热点深度分析**
   - 中东：伊朗核问题、巴以冲突、沙特伊朗关系
   - 东欧：俄乌冲突最新进展、欧洲安全架构
   - 亚太：中美竞争、台海局势、朝鲜半岛、南海争端
   - 美洲：美国政治、拉美左转、美洲峰会
   - 非洲：萨赫勒危机、东非局势

3. **全球经济形势**
   - 主要经济体表现
   - 贸易摩擦与供应链
   - 能源与粮食危机
   - 新兴市场挑战

4. **非传统安全挑战**
   - 气候变化
   - 网络安全
   - 恐怖主义
   - 公共卫生

5. **趋势预测与建议**
   - 未来3-6个月重要发展
   - 潜在风险点
   - 中国应对策略建议

要求：
- 专业、客观、有深度
- 约1200-1500字
- 使用Markdown格式
- 提供可操作的洞察"""

        prompt = "请撰写一份2026年5月的国际形势深度分析报告，要求专业、全面、有前瞻性。"
        
        response = await self._call_deepseek(prompt, system_prompt, temperature=0.3, max_tokens=3000)
        
        if response and not response.startswith("错误"):
            yield event.plain_result(f"📊 国际形势深度分析报告\n\n{response}")
        else:
            yield event.plain_result(f"❌ {response or '生成报告失败'}")
    
    @filter.command("region", alias={"地区", "地区分析"})
    async def analyze_region(self, event: AstrMessageEvent, region: str = ""):
        """分析特定地区形势，用法: /region <地区名>"""
        if not region:
            yield event.plain_result("""用法: /region <地区名>
            
常用地区：
• 中东 / Middle East
• 亚太 / Asia-Pacific
• 东欧 / Eastern Europe
• 西欧 / Western Europe
• 北美 / North America
• 拉美 / Latin America
• 非洲 / Africa
• 南亚 / South Asia
• 东南亚 / Southeast Asia""")
            return
        
        yield event.plain_result(f"🔍 正在分析 {region} 地区形势...")
        
        system_prompt = f"""你是研究{region}地区的顶级专家分析师。
请全面分析该地区当前形势，包括：

1. **地区概况**
   - 主要国家和势力
   - 地缘政治特点

2. **最新重要事件**
   - 政治动态
   - 军事冲突或合作
   - 经济变化

3. **关键问题分析**
   - 安全挑战
   - 经济困境或机遇
   - 社会矛盾

4. **外部影响**
   - 大国博弈
   - 国际组织角色
   - 区域合作机制

5. **趋势预测**
   - 未来3-6个月展望
   - 潜在风险与机遇
   - 对中国的影响

要求：
- 专业、客观、深入
- 约600-800字
- 使用Markdown格式"""

        prompt = f"请详细分析{region}地区在2026年5月的政治、安全、经济形势，包括最新动态、主要挑战和未来趋势。"
        
        response = await self._call_deepseek(prompt, system_prompt, temperature=0.4)
        
        if response and not response.startswith("错误"):
            yield event.plain_result(f"🌐 {region}地区形势分析\n\n{response}")
        else:
            yield event.plain_result(f"❌ {response or '分析失败'}")
    
    @filter.command("compare", alias={"对比", "比较"})
    async def compare_countries(self, event: AstrMessageEvent, country1: str = "", country2: str = ""):
        """对比分析两个国家，用法: /compare <国家1> <国家2>"""
        if not country1 or not country2:
            yield event.plain_result("""用法: /compare <国家1> <国家2>
            
示例：
• /compare 美国 中国
• /compare 俄罗斯 乌克兰
• /compare 以色列 伊朗
• /compare 印度 巴基斯坦""")
            return
        
        yield event.plain_result(f"⚖️ 正在对比分析 {country1} 和 {country2}...")
        
        system_prompt = f"""你是国际关系比较研究专家。
请全面对比分析{country1}和{country2}：

1. **基本国情对比**
   - 国土面积、人口、GDP
   - 政治体制
   - 军事实力

2. **外交战略**
   - 外交理念和政策
   - 盟友体系
   - 与对方关系史

3. **当前关系状态**
   - 合作领域
   - 竞争/冲突点
   - 最新互动

4. **地区/全球影响力**
   - 在各自地区角色
   - 全球治理参与
   - 软实力对比

5. **未来关系走向**
   - 短期趋势（3-6个月）
   - 长期展望
   - 可能情景

要求：
- 客观、平衡、有洞察力
- 约800-1000字
- 使用Markdown表格或分点对比
- 避免偏见，尊重事实"""

        prompt = f"请深入对比分析{country1}和{country2}在当前国际形势下的地位、双边关系、各自战略及未来走向。"
        
        response = await self._call_deepseek(prompt, system_prompt, temperature=0.3)
        
        if response and not response.startswith("错误"):
            yield event.plain_result(f"⚖️ {country1} vs {country2} 对比分析\n\n{response}")
        else:
            yield event.plain_result(f"❌ {response or '对比分析失败'}")
    
    @filter.command("hotspot", alias={"热点", "hot"})
    async def get_hotspots(self, event: AstrMessageEvent):
        """获取当前国际热点问题"""
        yield event.plain_result("🔥 正在识别当前国际热点...")
        
        system_prompt = """你是国际危机监测与预警专家。
请列出当前全球最值得关注的8-10个热点问题或潜在冲突点。

每个热点需包括：
- 📍 地点/国家/地区
- 🎯 核心问题
- 📊 当前状态（紧张/缓和/升级/僵持等）
- ⚠️ 风险等级（🔴高/🟡中/🟢低）
- 📝 简要说明（1-2句话）

要求：
- 简洁明了，直击要点
- 按风险等级排序
- 涵盖不同地区
- 控制在800字以内"""

        prompt = "请列出2026年5月全球最紧迫的国际热点问题和潜在冲突点，包括地缘政治、军事、经济等方面。"
        
        response = await self._call_deepseek(prompt, system_prompt, temperature=0.5)
        
        if response and not response.startswith("错误"):
            yield event.plain_result(f"🔥 国际热点问题\n\n{response}")
        else:
            yield event.plain_result(f"❌ {response or '获取热点失败'}")
    
    # ==================== 高级功能：文转图 ====================
    
    @filter.command("situation_pic", alias={"形势图", "图片报告"})
    async def situation_to_pic(self, event: AstrMessageEvent):
        """生成国际形势分析图片"""
        yield event.plain_result("🎨 正在生成分析图片，请稍候...")
        
        # 先获取分析内容
        system_prompt = """请生成一份简洁的国际形势摘要，用于生成图片报告。
要求：
1. 标题：国际形势简报
2. 时间：2026年5月
3. 内容：3-5个要点，每个要点一行
4. 每个要点格式：• 主题：简要说明
5. 控制在300字以内"""
        
        prompt = "生成当前国际形势简报，适合生成图片展示。"
        response = await self._call_deepseek(prompt, system_prompt, temperature=0.5)
        
        if not response or response.startswith("错误"):
            yield event.plain_result("❌ 生成内容失败")
            return
        
        # HTML模板 - 使用双花括号转义
        timestamp = self._get_timestamp()
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Arial', 'Microsoft YaHei', sans-serif;
            width: 800px;
            min-height: 600px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
        }}
        .title {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .timestamp {{
            font-size: 18px;
            color: #666;
        }}
        .content {{
            font-size: 20px;
            line-height: 1.8;
            color: #333;
            white-space: pre-wrap;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            color: #999;
            font-size: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">🌍 国际形势简报</div>
            <div class="timestamp">📅 {timestamp}</div>
        </div>
        <div class="content">{response}</div>
        <div class="footer">
            Powered by DeepSeek AI & AstrBot
        </div>
    </div>
</body>
</html>
"""
        
        try:
            # 生成图片
            image_url = await self.html_render(html_template, {}, options={"type": "png", "full_page": True})
            yield event.image_result(image_url)
        except Exception as e:
            logger.error(f"生成图片失败: {e}")
            yield event.plain_result(f"❌ 生成图片失败: {str(e)}")
    
    # ==================== 会话控制功能 ====================
    
    @filter.command("situation_chat", alias={"形势对话", "chat"})
    async def situation_chat(self, event: AstrMessageEvent):
        """开启国际形势对话模式"""
        user_name = event.get_sender_name()
        yield event.plain_result(f"💬 {user_name}，已进入国际形势对话模式！\n\n你可以直接提问关于国际形势的问题，发送「退出」结束对话。")
        
        @session_waiter(timeout=300, record_history_chains=True)
        async def chat_waiter(controller: SessionController, event: AstrMessageEvent):
            user_input = event.message_str.strip()
            
            if user_input == "退出":
                await event.send(event.plain_result("✅ 已退出对话模式"))
                controller.stop()
                return
            
            if not user_input:
                await event.send(event.plain_result("请输入您的问题~"))
                return
            
            await event.send(event.plain_result("🤔 正在思考..."))
            
            system_prompt = """你是国际形势分析专家，擅长回答各类国际政治、经济、军事问题。
要求：
1. 专业、客观、有深度
2. 基于事实，避免主观臆测
3. 适当引用数据和案例
4. 回答简洁明了，控制在300字以内
5. 如问题不清，可礼貌询问澄清"""
            
            response = await self._call_deepseek(user_input, system_prompt, temperature=0.6)
            
            if response and not response.startswith("错误"):
                message_result = event.make_result()
                message_result.chain = [Plain(f"💬 {response}")]
                await event.send(message_result)
            else:
                await event.send(event.plain_result(f"❌ {response or '处理失败'}"))
            
            controller.keep(timeout=300, reset_timeout=True)
        
        try:
            await chat_waiter(event)
        except TimeoutError:
            yield event.plain_result("⏰ 对话超时，已自动退出")
        except Exception as e:
            logger.error(f"对话模式错误: {e}")
            yield event.plain_result("❌ 发生错误，已退出对话")
        finally:
            event.stop_event()
    
    # ==================== 帮助信息 ====================
    
    @filter.command("situation_help", alias={"形势帮助", "国际帮助"})
    async def show_help(self, event: AstrMessageEvent):
        """显示插件帮助信息"""
        help_text = """🌍 国际形势分析插件 v3.0 - 帮助

📋 基础指令：
/situation (形势) - AI分析国际形势摘要
/situation_detail (深度分析) - 深度分析报告
/region <地区> (地区) - 分析特定地区
/compare <国1> <国2> (对比) - 国家对比分析
/hotspot (热点) - 查看国际热点

🎨 可视化：
/situation_pic (形势图) - 生成分析图片

💬 交互功能：
/situation_chat (形势对话) - 对话模式，可连续提问

🔧 配置指令：
/situation_help (帮助) - 显示此帮助

💡 使用技巧：
• 所有分析由 DeepSeek AI 驱动
• 基于模型知识（截至2024年）
• 支持指令别名，如 /形势、/热点
• 对话模式支持连续多轮问答
• 可生成美观的图片报告

⚙️ 配置项：
• DeepSeek API Key（已配置）
• AI温度参数
• 最大令牌数
• 分析语言
        yield event.plain_result(help_text)
    
    # ==================== 生命周期管理 ====================
    
    async def terminate(self):
        """插件卸载时调用"""
        logger.info("国际形势分析插件已卸载")
