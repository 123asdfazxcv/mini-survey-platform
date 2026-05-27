"""
迷你模拟消费者调研平台
======================
固定人设: 28岁二线城市、月入8k、高频护肤女性消费者
用法: python app.py
"""

import os
import json
import re
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- API 配置 ---
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_AVAILABLE = False
anthropic_client = None

if API_KEY:
    try:
        import anthropic as anthropic_sdk
        anthropic_client = anthropic_sdk.Anthropic(api_key=API_KEY)
        ANTHROPIC_AVAILABLE = True
        print("[OK] Anthropic API 已就绪")
    except ImportError:
        print("[WARN] anthropic 库未安装，将使用 Mock 模式。安装: pip install anthropic")
    except Exception as e:
        print(f"[WARN] Anthropic 初始化失败: {e}，将使用 Mock 模式。")
else:
    print("[INFO] 未设置 ANTHROPIC_API_KEY，将使用 Mock 模式。")
    print("[INFO] 设置方式: set ANTHROPIC_API_KEY=your_key 后重启")

# --- 多用户人设库 ---
PERSONAS = {
    "xiaolin": {
        "id": "xiaolin",
        "name": "小琳",
        "avatar": "&#128129;",
        "age": "28岁", "city": "杭州", "job": "互联网运营",
        "stats": [
            {"value": "&yen;8k", "label": "月收入"},
            {"value": "&yen;1&ndash;2k", "label": "月护肤支出"},
            {"value": "5&times;/周", "label": "护肤频率"},
        ],
        "tags": ["成分党", "偏好国货+日韩", "理性种草", "抗初老 & 美白", "大促囤货型"],
        "quick_prompts": [
            ("你平时怎么挑选美白精华？", "美白精华选购"),
            ("你一个月在护肤品上花多少钱？怎么分配的？", "预算分配策略"),
            ("你对现在流行的国货护肤品牌怎么看？", "国货品牌态度"),
            ("你会跟风买小红书推荐的产品吗？为什么？", "种草与决策"),
            ("618你打算囤哪些护肤品？", "大促囤货计划"),
            ("你有没有去过美容院或者做过医美？觉得值不值？", "美容院 & 医美"),
        ],
        "system_prompt": """你是一个模拟消费者，请严格按照以下人设回答调研问题：

【基本信息】姓名：小琳 / 年龄：28岁 / 性别：女 / 城市：杭州（二线）/ 职业：互联网运营 / 月收入：8000元 / 月护肤支出：1000-2000元

【消费特征】高频护肤消费者；注重性价比不追大牌；成分党，买前查测评；易被小红书抖音种草但理性比较后下单；偏好国货（珀莱雅、薇诺娜）和日韩品牌（芙丽芳丝）；大促集中囤货。

【答题要求】第一人称"我"回答，语气自然真实，有具体产品/价格/使用感受，100-200字。""",
        "mock_templates": [
            {"keywords": ["美白","白","暗沉","肤色","淡斑","色斑"], "answer": "美白是我最在意的护肤功课！用了很多产品，觉得烟酰胺+维C组合最有效。目前在用珀莱雅双抗精华（200出头），搭薇诺娜防晒，坚持小半年白了一个度。美白是长期工程，防晒比精华更重要。预算有限的话我会优先买好的防晒。"},
            {"keywords": ["面膜","补水","保湿"], "answer": "面膜一周敷3-4次，片状和涂抹换着来。片状单片超15块就嫌贵，618囤自然堂和珀莱雅平均七八块一片。涂抹式在用科颜氏白泥（小样先试的）和芙丽芳丝，挺好用的。"},
            {"keywords": ["精华","抗老","抗初老","抗衰","皱纹"], "answer": "精华是我最舍得花钱的品类，200-400区间。抗初老从25岁开始，关注二裂酵母、玻色因、视黄醇。现在用红宝石精华觉得性价比很高，一百多块成分表很能打。小棕瓶好用但太贵了，月薪8k下不去手哈哈。"},
            {"keywords": ["品牌","国货","大牌","牌子"], "answer": "国货真的做得很好！我化妆台80%是国货和日韩，珀莱雅、薇诺娜、至本、HBN轮着用。成分肤感不输大牌，价格便宜太多。大牌先买小样试试，好用再等大促入正装。现在护肤品卷得很，消费者反而受益。"},
            {"keywords": ["价格","预算","贵","便宜","消费","花钱","省钱"], "answer": "月薪8k在杭州不算宽裕，每月护肤预算1500已经是比较舍得的部分了。精华面霜买好点（200-400），水乳洁面选性价比高的（100以内），面膜趁大促囤。贵价产品先买小样，合适再入正装，不踩雷也不心疼。"},
            {"keywords": ["防晒","清洁","洁面","卸妆","水乳","面霜"], "answer": "基础护肤注重实用。洁面用至本氨基酸（50多块），水用HABA G露，面霜冬珂润夏薇诺娜。防晒一年四季都涂，碧柔和安耐晒换着用。防晒是最值得投资的护肤品，比什么精华都重要。"},
            {"keywords": ["购物","渠道","淘宝","京东","小红书","直播","种草"], "answer": "基本都在线上买，618双11囤货最划算。先在小红书和抖音看测评，关注成分博主做功课。直播间偶尔蹲，但不冲动消费，提前看好的产品等主播上了再买。线下逛屈臣氏和话梅，主要试色号和质地。"},
            {"keywords": ["美容院","医美","项目"], "answer": "美容院一个月去1-2次做基础清洁补水，一次150-200，预算300-400/月。医美还没尝试，价格偏高也有点怕。朋友做了光子嫩肤说效果不错，考虑年底发年终奖去试一次，但得先做足功课。"},
        ],
        "mock_fallback": "这个问题挺有意思的。作为一个经常研究护肤品的人，我觉得还是得看具体需求和成分，不能盲目跟风。预算范围内选最适合自己的才是王道。",
    },

    "daliu": {
        "id": "daliu",
        "name": "大刘",
        "avatar": "&#128104;&#8205;&#128187;",
        "age": "35岁", "city": "深圳", "job": "产品经理",
        "stats": [
            {"value": "&yen;25k", "label": "月收入"},
            {"value": "&yen;3&ndash;5k", "label": "数码/汽车月支出"},
            {"value": "2&times;/月", "label": "户外频率"},
        ],
        "tags": ["数码控", "新能源车主", "户外露营党", "请客型消费", "注重效率"],
        "quick_prompts": [
            ("你买手机最看重什么？预算多少？", "手机选购观"),
            ("你的新能源车使用体验怎么样？后悔吗？", "新能源车体验"),
            ("你平时周末会去露营吗？装备大概花了多少？", "户外露营消费"),
            ("你和朋友聚餐一般怎么安排？人均多少？", "社交餐饮习惯"),
            ("你最近买的最值的数码产品是什么？", "数码好物推荐"),
            ("你觉得男人有必要花钱护肤吗？", "男性护肤态度"),
        ],
        "system_prompt": """你是模拟消费者，严格按以下人设回答调研问题：

【基本信息】姓名：大刘 / 年龄：35岁 / 性别：男 / 城市：深圳（一线）/ 职业：产品经理 / 月收入：25000元 / 数码+汽车月支出3000-5000元

【消费特征】数码重度用户（手机/耳机/笔记本每年换新，关注评测不盲从）；2024年换了比亚迪海豹，关注续航和智驾；周末喜欢露营和徒步（装备迪卡侬混搭始祖鸟，总投入约1.5w）；社交请客型消费（人均200-400能接受）；对效率工具和付费软件愿意花钱。

【答题要求】第一人称"我"回答，语气务实直接，有具体产品/价格/对比，100-200字。""",
        "mock_templates": [
            {"keywords": ["手机","数码","耳机","电脑","笔记本","电子产品"], "answer": "手机我基本一年一换，现在用的小米15 Pro。选机主要看屏幕和续航，拍照反而没那么在意。预算5000-7000比较舒服，超过1万就觉得溢价太严重了。耳机用的索尼WH-1000XM5，降噪真的好用，出差必备。"},
            {"keywords": ["车","新能源","充电","续航","驾驶"], "answer": "去年换了比亚迪海豹，落地18万出头。续航标称700实际跑550左右，深圳充电桩多倒没什么焦虑。最满意的是智能驾驶辅助，堵车的时候轻松不少。但车机偶尔卡顿这点不太爽，30万预算的话我可能会选蔚来。"},
            {"keywords": ["露营","户外","徒步","运动","装备"], "answer": "露营装备七七八八花了一万五左右。帐篷和睡袋买了挪客的，性价比不错。冲锋衣倒是狠心入了件始祖鸟Beta AR（4000多），确实防风防水但说实话迪卡侬499的也能用。我的原则是保命的装备买好的，装饰性的够用就行。"},
            {"keywords": ["吃饭","聚餐","请客","餐厅","美食","社交"], "answer": "朋友聚餐一般我来组局，人均200-400算正常范围。喜欢找那种有特色的店，不一定是贵的。请客的话控制在人均300以内，一个月请个两三次。自己平时吃饭就比较随便了，外卖或者楼下快餐解决，半小时内搞定。"},
            {"keywords": ["护肤","保养","形象","打扮"], "answer": "男人护肤我觉得有必要但不用过度。我每天就三步：洁面+水+防晒，五分钟搞定。用的LAB SERIES一套大概五六百，能用三四个月，比女生的护肤成本低多了。主要诉求就是干净不油腻，抗老什么的还没太关注。"},
            {"keywords": ["预算","消费","花钱","省钱","贵","便宜"], "answer": "月入25k在深圳只能说中等，房贷就去掉8000。我的消费观是该花的不省，数码产品、出行体验、请客社交这些我愿意花钱，但衣服就优衣库搞定。每个月固定存5000，剩下的花完不焦虑。活得明白比较重要。"},
        ],
        "mock_fallback": "这个问题我得想一下。我的消费逻辑比较简单：核心体验的东西舍得花钱，周边的够用就行。时间比钱更值钱，所以效率对我来说很重要。",
    },

    "zhangyi": {
        "id": "zhangyi",
        "name": "张姨",
        "avatar": "&#128105;&#8205;&#127859;",
        "age": "52岁", "city": "洛阳", "job": "退休教师",
        "stats": [
            {"value": "&yen;5k", "label": "月退休金"},
            {"value": "&yen;800&ndash;1.5k", "label": "保健品/养生月支出"},
            {"value": "每天", "label": "广场舞频率"},
        ],
        "tags": ["养生达人", "广场舞爱好者", "疼孙辈", "比价能手", "抖音重度用户"],
        "quick_prompts": [
            ("你平时买什么保健品？觉得真的有用吗？", "保健品消费观"),
            ("你最舍得在哪方面花钱？", "消费重心"),
            ("你会给孙子孙女买什么东西？预算多少？", "孙辈消费"),
            ("你买菜一般去哪买？一个月花多少？", "生鲜采买习惯"),
            ("你刷抖音会买东西吗？踩过坑吗？", "短视频购物"),
        ],
        "system_prompt": """你是模拟消费者，严格按以下人设回答调研问题：

【基本信息】姓名：张姨 / 年龄：52岁 / 性别：女 / 城市：洛阳（三线）/ 职业：退休教师 / 月退休金：5000元 / 保健品+养生月支出800-1500元

【消费特征】注重养生（吃钙片、鱼油、辅酶Q10，定期体检）；广场舞活跃分子（买过3套队服+蓝牙音箱）；疼孙辈（舍得给外孙买玩具和衣服，但会和儿媳商量）；比价老手（买菜认准早市，超市晚上打折才去）；抖音购物新手（被种草过几次但遇到过货不对板）。

【答题要求】第一人称"我"回答，语气亲切家常，有具体品牌/价格，100-200字。""",
        "mock_templates": [
            {"keywords": ["保健","养生","钙片","鱼油","维生素","健康"], "answer": "我每天早上吃一粒钙片一粒鱼油，都是女儿在网上给我买的，说汤臣倍健的牌子好。吃了两年多，感觉腿脚确实利索了些。最近又加了辅酶Q10，说是对心脏好。一个月这些大概花三四百，我觉得这钱花得值，身体好比什么都强。"},
            {"keywords": ["广场舞","跳舞","运动","锻炼"], "answer": "我们广场舞队有二十来号人，我算是积极分子！队服买了好几套，一套七八十不贵。最贵的是那个蓝牙音箱，两百多块大家一起凑的，音量大续航也长。跳舞这几年最大的变化是睡眠好了，人也开心了。这比吃保健品管用！"},
            {"keywords": ["孙子","孙女","孙辈","小孩","孩子","玩具"], "answer": "我外孙今年四岁，每次看到玩具就走不动道。我一般一个月给他买一两样，控制在两百块以内。上次买个乐高花了两百多，被他妈妈说了，说太贵了。后来就买些几十块的小汽车小恐龙，孩子一样玩得开心。太贵的我现在会先问女儿意见。"},
            {"keywords": ["买菜","菜市场","超市","生鲜","水果"], "answer": "买菜我认准早市，七点去最新鲜还便宜。一个月菜钱大概六七百，两个人吃。超市我都是晚上八点后去，熟食和生鲜会打折。盒马也去过两次，东西是新鲜但太贵了，我这退休工资消费不起。还是菜市场最实惠。"},
            {"keywords": ["抖音","直播","网购","网上","快递"], "answer": "抖音我天天刷，也买过几次东西。买过一个拖把倒是挺好用，但买过一件毛衣色差太大了直接退了。现在学聪明了，多看评论特别是差评，好评可能是刷的。贵的东西还是在淘宝买，抖音上就买些小玩意儿。"},
        ],
        "mock_fallback": "哎呀，这个问题我得好好想想。我们这个年纪的人，花钱比较谨慎，毕竟退休金就那么些。但该花的地方也不会太省，健康最重要。",
    },

    "ajie": {
        "id": "ajie",
        "name": "阿杰",
        "avatar": "&#128102;",
        "age": "22岁", "city": "上海", "job": "初级程序员",
        "stats": [
            {"value": "&yen;6k", "label": "月收入"},
            {"value": "&yen;1.5k", "label": "外卖月支出"},
            {"value": "每周5&ndash;6次", "label": "点外卖频率"},
        ],
        "tags": ["外卖达人", "手游月卡党", "B站重度用户", "球鞋关注者", "合租省钱党"],
        "quick_prompts": [
            ("你一个月外卖花多少钱？最爱点什么？", "外卖消费习惯"),
            ("你在游戏上花钱吗？每个月氪多少？", "游戏氪金态度"),
            ("你对潮牌球鞋怎么看？买过最贵的是哪双？", "球鞋消费观"),
            ("你租房的体验怎么样？房租占收入多少？", "租房与生活成本"),
            ("你最舍得在哪方面花钱？", "消费优先级"),
        ],
        "system_prompt": """你是模拟消费者，严格按以下人设回答调研问题：

【基本信息】姓名：阿杰 / 年龄：22岁 / 性别：男 / 城市：上海（一线）/ 职业：初级程序员 / 月收入：6000元 / 外卖月支出约1500元

【消费特征】外卖高频用户（一周点5-6次，客单价25-40，爱点炸鸡汉堡麻辣烫）；手游玩家（原神月卡党+偶尔首充，月均100-200）；关注球鞋和潮牌但预算有限，买平替或折扣款；B站大会员+网盘会员，愿意为内容付费；合租族（房租2500，最大开支），日常消费追求性价比。

【答题要求】第一人称"我"回答，语气随性真实，有具体价格和平台/品牌，100-200字。""",
        "mock_templates": [
            {"keywords": ["外卖","吃饭","点餐","饿了么","美团","吃"], "answer": "外卖一周点五六次是常态，加班没时间做饭。最爱点炸鸡和麻辣烫，客单价25-40。一个月外卖大概花1500左右，上海这个消费水平没办法。偶尔领到美团的大额券会开心一整天，感觉像捡到钱。"},
            {"keywords": ["游戏","氪金","充值","原神","崩铁","王者","手游"], "answer": "原神我玩了一年多了，月卡30块雷打不动，偶尔遇到喜欢的角色会氪个首充198。一个月游戏花100-200，算是我为数不多的娱乐消费了。648是不可能648的，月薪6k在上海活下去已经很不容易了哈哈。"},
            {"keywords": ["球鞋","潮牌","衣服","穿搭","鞋"], "answer": "球鞋确实喜欢但买不起贵的，最贵的一双是双十一抢的Air Force 1，六百多。平时穿回力和安踏的平替款，两三百一双也好搭。潮牌的话就买优衣库和GU，干净舒服就行。等涨工资了第一件事就是入一双AJ。"},
            {"keywords": ["租房","房租","房租","水电","生活成本"], "answer": "房租2500是我每月最大的痛，占了收入的40%还多。在浦东和同事合租，一间十几平，怎么说呢就一张床一张桌。电费夏天开空调巨贵。想过搬远一点便宜但通勤太久，每天地铁来回两小时已经是极限了。"},
            {"keywords": ["B站","大会员","视频","内容","付费","订阅"], "answer": "B站大会员连开两年了，一年148我觉得还行。还有百度网盘的SVIP，下载资源刚需。一个月订阅服务大概五六十块。我的原则是，好的内容我愿意付费，但不会为烂内容花一分钱。这也是程序员的一点坚持吧。"},
        ],
        "mock_fallback": "呃这个问题让我想想。刚毕业嘛，工资在上海真的不够花，每个月基本月光。但我觉得刚工作前两年不用太焦虑存钱，先提升自己比较重要。",
    },

    "lily": {
        "id": "lily",
        "name": "Lily",
        "avatar": "&#128134;",
        "age": "30岁", "city": "成都", "job": "市场经理",
        "stats": [
            {"value": "&yen;18k", "label": "月收入"},
            {"value": "&yen;2&ndash;3k", "label": "健身/宠物月支出"},
            {"value": "4&times;/周", "label": "健身频率"},
        ],
        "tags": ["CrossFit爱好者", "猫奴一枚", "轻奢包包控", "咖啡探店达人", "悦己型消费"],
        "quick_prompts": [
            ("你在健身上花了多少钱？觉得值得吗？", "健身消费观"),
            ("你养猫一个月大概花多少？", "宠物消费明细"),
            ("你买包会选轻奢还是大牌？预算多少？", "包包消费态度"),
            ("你周末喜欢探什么类型的咖啡店？", "探店消费习惯"),
            ("你怎么平衡存钱和悦己消费？", "消费与储蓄平衡"),
        ],
        "system_prompt": """你是模拟消费者，严格按以下人设回答调研问题：

【基本信息】姓名：Lily / 年龄：30岁 / 性别：女 / 城市：成都（新一线）/ 职业：市场经理 / 月收入：18000元 / 健身+宠物月支出2000-3000元

【消费特征】CrossFit爱好者（年卡+私教每月约1500）；猫奴（布偶猫"年糕"，月均猫粮+猫砂+保险500）；轻奢包爱好者（一年买1-2个，预算3-5k，Coach/Tory Burch/MK档位）；咖啡探店达人（周末必打卡，每月500-800）；悦己型消费（SPA/美甲月均500），愿意为体验和质感花钱。

【答题要求】第一人称"我"回答，语气精致自然，有具体品牌/价格，100-200字。""",
        "mock_templates": [
            {"keywords": ["健身","运动","私教","CrossFit","锻炼"], "answer": "健身是我生活中最固定的支出了。CrossFit年卡8000多，再加私教课一个月大概1500。很多人觉得贵，但我算了一下，除以去的次数其实还好。而且健身后整个人的状态和自信都不一样了，这钱花得特别值，比买包还值。"},
            {"keywords": ["猫","宠物","猫粮","猫砂","布偶"], "answer": "我家布偶叫年糕，妥妥的四脚吞金兽！每个月猫粮300+猫砂100+保险100，再加上零食和玩具，差不多五六百。上次尿闭去趟宠物医院直接2000+，宠物医保真的很重要。但每天回家它来蹭我的时候，觉得一切都值了。"},
            {"keywords": ["包","包包","轻奢","Coach","Tory Burch","MK"], "answer": "包我喜欢轻奢档位的，一年入1-2个。Coach和Tory Burch是我常买的牌子，一个三千到五千，质感不错背出去也体面。大牌LV Gucci那种一两万的目前还舍不得，觉得花一个月工资买个包有点过了。等升职加薪再说吧。"},
            {"keywords": ["咖啡","探店","打卡","下午茶","周末"], "answer": "周末最期待的就是探新开的咖啡店！成都好店太多了，一周去2-3家。一杯手冲三四十，加块蛋糕六七十，一个月探店大概花500-800。花的不仅是咖啡钱，更是一个美好的周末下午。最近在尝试学拉花，感觉可以省点钱了哈哈。"},
            {"keywords": ["存钱","储蓄","理财","预算","工资","消费观"], "answer": "月入18k在成都生活挺舒服的，每个月固定存5000到理财，剩下的花完也不太焦虑。我的理念是存钱和悦己要平衡——30岁了，既要有安全感，也要享受当下。除了固定存款，健身和猫是雷打不动的预算，包包和探店会根据当月剩余灵活调整。"},
        ],
        "mock_fallback": "这个问题我挺有感触的。30岁是一个开始思考消费意义的年龄。我的原则是不委屈自己，但也不乱花钱。每一笔消费如果让我开心或者变得更好，那就是值得的。",
    },
}

DEFAULT_PERSONA = "xiaolin"


def mock_answer(question: str, persona_id: str) -> dict:
    """根据问题关键词匹配 mock 回答，返回含情感标签和追问的dict"""
    p = PERSONAS.get(persona_id, PERSONAS[DEFAULT_PERSONA])
    q = question.lower()
    answer = p["mock_fallback"]
    for t in p["mock_templates"]:
        for kw in t["keywords"]:
            if kw.lower() in q:
                answer = t["answer"]
                break
        if answer != p["mock_fallback"]:
            break
    return {
        "answer": answer,
        "sentiment": classify_sentiment(answer),
        "follow_ups": generate_follow_ups(persona_id, question, answer),
    }


def call_anthropic(question: str, persona_id: str) -> dict:
    """调用 Anthropic API 生成回答，含结构化情感标签和追问"""
    p = PERSONAS.get(persona_id, PERSONAS[DEFAULT_PERSONA])
    prompt = p["system_prompt"] + """

请在回答后附加以下格式（不要遗漏）：
[情感]种草/中立/吐槽（三选一）
[追问1]一个相关的追问
[追问2]另一个相关的追问"""
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0.8,
        system=prompt,
        messages=[{
            "role": "user",
            "content": f"调研问题：{question}\n\n请以这个消费者的身份，用第一人称自然回答。"
        }]
    )
    raw = response.content[0].text.strip()
    # 解析结构化输出
    answer = raw
    sentiment = "中立"
    follow_ups = []
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("[情感]") or line.startswith("情感："):
            s = line.replace("[情感]","").replace("情感：","").strip()
            if "种草" in s: sentiment = "种草"
            elif "吐槽" in s: sentiment = "吐槽"
            else: sentiment = "中立"
        elif line.startswith("[追问1]") or line.startswith("追问1") or line.startswith("1."):
            fu = line.split("]",1)[-1].strip() if "]" in line else line.split(".")[-1].strip()
            if fu: follow_ups.append(fu)
        elif line.startswith("[追问2]") or line.startswith("追问2") or line.startswith("2."):
            fu = line.split("]",1)[-1].strip() if "]" in line else line.split(".")[-1].strip()
            if fu: follow_ups.append(fu)
    # 清理回答（去掉结构化标签行）
    tags_to_strip = ["[情感]","情感：","[追问","追问","1.","2."]
    clean_lines = [l for l in raw.split("\n") if not any(
        l.strip().startswith(p) for p in tags_to_strip)]
    answer = "\n".join(clean_lines).strip()
    if not follow_ups:
        follow_ups = generate_follow_ups(persona_id, question, answer)
    return {
        "answer": answer or raw,
        "sentiment": sentiment,
        "follow_ups": [{"text": f, "label": f} for f in follow_ups[:3]],
    }


# --- 情感分类器 ---
POSITIVE_WORDS = ["喜欢","好用","推荐","值得","满意","划算","实惠","方便","开心",
    "舒服","不错","好 ","爱 ","便宜","超值","棒","囤","回购","种草","必买","值了","绝了",
    "性价比高","最爱","必要","重要","愿意","花得值","提升","享受"]
NEGATIVE_WORDS = ["贵","差","坑","后悔","不好","不行","失望","浪费","太贵","不值",
    "踩雷","垃圾","骗","心疼","下不去手","买不起","消费不起","不划算","不推荐","踩坑",
    "智商税","割韭菜","不好用","烂","差评"]

def classify_sentiment(text: str) -> str:
    """对回答文本进行情感分类"""
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    if pos > neg + 1: return "种草"
    if neg > pos + 1: return "吐槽"
    return "中立"

def generate_follow_ups(persona_id: str, question: str, answer: str) -> list:
    """基于上下文生成智能追问"""
    p = PERSONAS.get(persona_id, PERSONAS[DEFAULT_PERSONA])
    # 从快捷问题中筛选相关追问
    candidates = []
    q_words = set(question.replace("？","").replace("?",""))
    for q_text, q_label in p["quick_prompts"]:
        # 避免追问与当前问题完全相同
        if q_text != question:
            candidates.append((q_text, q_label))
    # 选2-3个最相关的
    return [{"text": t, "label": l} for t, l in candidates[:3]]


# --- 场景化测试问题库 ---
SCENARIOS = {
    "xiaolin": [
        ("如果某大牌（比如兰蔻）推出200元以内的平价线，你会从国货转投吗？", "大牌平价线冲击"),
        ("如果直播间送你一堆小样，你会冲动下单正装吗？", "小样诱惑测试"),
        ("如果珀莱雅涨价30%，你还会继续买吗？", "国货涨价测试"),
        ("如果闺蜜强烈推荐一个你没听过的品牌，你会买吗？", "社交推荐测试"),
    ],
    "daliu": [
        ("如果苹果手机降价20%，你会从安卓转回iPhone吗？", "苹果降价测试"),
        ("如果新能源车补贴取消，你还会买电车吗？", "补贴取消测试"),
        ("如果迪卡侬和始祖鸟联名出平价冲锋衣，你会买吗？", "联名平价测试"),
    ],
    "zhangyi": [
        ("如果保健品买二送一，你会一次囤半年量吗？", "囤货测试"),
        ("如果邻居推荐了一个很贵但据说效果很好的按摩仪，你会买吗？", "高价推荐测试"),
        ("如果广场舞比赛需要统一买200元的新队服，你会同意吗？", "集体消费测试"),
    ],
    "ajie": [
        ("如果外卖会员涨价30%，你还会续费吗？", "外卖涨价测试"),
        ("如果原神下一个限定角色强度超高，你会破例氪648吗？", "游戏氪金测试"),
        ("如果公司搬到更远的地方但房租便宜500，你会搬家吗？", "通勤vs房租测试"),
    ],
    "lily": [
        ("如果健身房突然涨价20%，你会续卡还是换一家？", "健身涨价测试"),
        ("如果猫生病需要花5000做手术，你会毫不犹豫吗？", "宠物医疗测试"),
        ("如果Coach出一个只要1500的限量款，你会冲动下手吗？", "轻奢降价测试"),
    ],
}

# --- HTML 模板 ---
HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mini Consumer Survey | AI Simulation</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  /* ============================================
     5 Warm-Tone Themes via CSS Custom Properties
     ============================================ */

  /* 1. 暖杏 — 杏色底，柔和明亮，默认主题 */
  body[data-theme="apricot"] {
    --bg: #fdf8f3;
    --bg-soft: #faf4ed;
    --bg-card: #ffffff;
    --text-primary: #3e3230;
    --text-secondary: #6b5d58;
    --text-muted: #a3968e;
    --accent: #d4956a;
    --accent-strong: #c1784a;
    --accent-soft: #f0d5c0;
    --accent-dim: #e8c4a8;
    --border: #ece0d5;
    --border-light: #f5ede5;
    --stat-bg: #fdf6f0;
    --input-bg: #fdf8f4;
    --input-border: #e8dbcf;
    --tag-bg: #fdf6f0;
    --tag-border: #f0d5c0;
    --shadow: 0 1px 3px rgba(80,40,20,0.04), 0 4px 16px rgba(80,40,20,0.04);
    --shadow-hover: 0 1px 3px rgba(80,40,20,0.06), 0 6px 24px rgba(80,40,20,0.06);
    --orb-1: rgba(212,149,106,0.18);
    --orb-2: rgba(193,120,74,0.10);
  }

  /* 2. 蜜桃 — 蜜桃粉，甜美清新 */
  body[data-theme="peach"] {
    --bg: #fef5f5;
    --bg-soft: #fdf0f0;
    --bg-card: #ffffff;
    --text-primary: #3d2e33;
    --text-secondary: #6b555b;
    --text-muted: #a38b90;
    --accent: #d4857b;
    --accent-strong: #c1706a;
    --accent-soft: #f2ceca;
    --accent-dim: #eabfb8;
    --border: #f0dedb;
    --border-light: #f8edeb;
    --stat-bg: #fef7f6;
    --input-bg: #fef8f7;
    --input-border: #edd5d2;
    --tag-bg: #fef7f6;
    --tag-border: #f2ceca;
    --shadow: 0 1px 3px rgba(80,30,30,0.04), 0 4px 16px rgba(80,30,30,0.04);
    --shadow-hover: 0 1px 3px rgba(80,30,30,0.06), 0 6px 24px rgba(80,30,30,0.06);
    --orb-1: rgba(212,133,123,0.18);
    --orb-2: rgba(193,112,106,0.10);
  }

  /* 3. 燕麦 — 奶咖色，温柔知性 */
  body[data-theme="oat"] {
    --bg: #f9f6f1;
    --bg-soft: #f5f1ea;
    --bg-card: #ffffff;
    --text-primary: #3d3832;
    --text-secondary: #6b6359;
    --text-muted: #a3988c;
    --accent: #c4a882;
    --accent-strong: #af8f65;
    --accent-soft: #e8daca;
    --accent-dim: #dfceb8;
    --border: #e8e0d4;
    --border-light: #f2ece4;
    --stat-bg: #faf7f2;
    --input-bg: #faf7f3;
    --input-border: #e5dbcc;
    --tag-bg: #faf7f2;
    --tag-border: #e8daca;
    --shadow: 0 1px 3px rgba(60,40,20,0.04), 0 4px 16px rgba(60,40,20,0.04);
    --shadow-hover: 0 1px 3px rgba(60,40,20,0.06), 0 6px 24px rgba(60,40,20,0.06);
    --orb-1: rgba(196,168,130,0.18);
    --orb-2: rgba(175,143,101,0.10);
  }

  /* 4. 琥珀 — 琥珀暖金，精致温暖 */
  body[data-theme="amber"] {
    --bg: #fdf7ef;
    --bg-soft: #faf2e6;
    --bg-card: #ffffff;
    --text-primary: #3e3328;
    --text-secondary: #6b5a48;
    --text-muted: #a3927c;
    --accent: #d4a35a;
    --accent-strong: #c18e3e;
    --accent-soft: #f0dbb8;
    --accent-dim: #e8cfa0;
    --border: #ece0c8;
    --border-light: #f5eddc;
    --stat-bg: #fdf8f1;
    --input-bg: #fdf9f2;
    --input-border: #e8dcc8;
    --tag-bg: #fdf8f1;
    --tag-border: #f0dbb8;
    --shadow: 0 1px 3px rgba(80,50,10,0.04), 0 4px 16px rgba(80,50,10,0.04);
    --shadow-hover: 0 1px 3px rgba(80,50,10,0.06), 0 6px 24px rgba(80,50,10,0.06);
    --orb-1: rgba(212,163,90,0.18);
    --orb-2: rgba(193,142,62,0.10);
  }

  /* 5. 玫瑰 — 干枯玫瑰，优雅浪漫（稍深） */
  body[data-theme="rose"] {
    --bg: #faf4f3;
    --bg-soft: #f6eeed;
    --bg-card: #ffffff;
    --text-primary: #3d2f30;
    --text-secondary: #6b5456;
    --text-muted: #a38a8b;
    --accent: #c0847c;
    --accent-strong: #ad6b63;
    --accent-soft: #ebceca;
    --accent-dim: #e2bdb8;
    --border: #eedad7;
    --border-light: #f6eae8;
    --stat-bg: #fbf5f4;
    --input-bg: #fbf6f5;
    --input-border: #ebd6d3;
    --tag-bg: #fbf5f4;
    --tag-border: #ebceca;
    --shadow: 0 1px 3px rgba(80,30,30,0.04), 0 4px 16px rgba(80,30,30,0.04);
    --shadow-hover: 0 1px 3px rgba(80,30,30,0.06), 0 6px 24px rgba(80,30,30,0.06);
    --orb-1: rgba(192,132,124,0.16);
    --orb-2: rgba(173,107,99,0.09);
  }

  /* Shared defaults (暖杏 fallback) */
  body {
    --bg: #fdf8f3;
    --bg-soft: #faf4ed;
    --bg-card: #ffffff;
    --text-primary: #3e3230;
    --text-secondary: #6b5d58;
    --text-muted: #a3968e;
    --accent: #d4956a;
    --accent-strong: #c1784a;
    --accent-soft: #f0d5c0;
    --accent-dim: #e8c4a8;
    --border: #ece0d5;
    --border-light: #f5ede5;
    --stat-bg: #fdf6f0;
    --input-bg: #fdf8f4;
    --input-border: #e8dbcf;
    --tag-bg: #fdf6f0;
    --tag-border: #f0d5c0;
    --shadow: 0 1px 3px rgba(80,40,20,0.04), 0 4px 16px rgba(80,40,20,0.04);
    --shadow-hover: 0 1px 3px rgba(80,40,20,0.06), 0 6px 24px rgba(80,40,20,0.06);
    --orb-1: rgba(212,149,106,0.18);
    --orb-2: rgba(193,120,74,0.10);

    --radius-sm: 8px;
    --radius: 14px;
    --radius-lg: 20px;
    --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);

    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    min-height: 100vh; color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    line-height: 1.6;
    transition: background var(--transition), color var(--transition);
  }

  /* Background orbs */
  .bg-orb { position: fixed; border-radius: 50%; filter: blur(100px); pointer-events: none; z-index: 0; transition: background var(--transition); }
  .bg-orb.orb-1 {
    width: 520px; height: 520px; top: -200px; right: -160px;
    background: radial-gradient(circle, var(--orb-1) 0%, transparent 70%);
  }
  .bg-orb.orb-2 {
    width: 380px; height: 380px; bottom: -100px; left: -100px;
    background: radial-gradient(circle, var(--orb-2) 0%, transparent 70%);
  }

  .container { max-width: 680px; margin: 0 auto; padding: 32px 24px 56px; position: relative; z-index: 1; }

  /* ======= Theme Switcher ======= */
  .theme-bar {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    padding: 8px 0 20px;
  }
  .theme-bar .theme-label {
    font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
    color: var(--text-muted); text-transform: uppercase; margin-right: 4px;
  }
  .theme-dot {
    width: 28px; height: 28px; border-radius: 50%; cursor: pointer;
    border: 2px solid transparent; transition: all var(--transition);
    position: relative; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }
  .theme-dot:hover { transform: scale(1.15); }
  .theme-dot.active { border-color: var(--text-primary); box-shadow: 0 0 0 3px var(--border); }
  .theme-dot[data-theme="apricot"] { background: linear-gradient(135deg, #fdf8f3, #e8c4a8); }
  .theme-dot[data-theme="peach"]   { background: linear-gradient(135deg, #fef5f5, #eabfb8); }
  .theme-dot[data-theme="oat"]     { background: linear-gradient(135deg, #f9f6f1, #dfceb8); }
  .theme-dot[data-theme="amber"]   { background: linear-gradient(135deg, #fdf7ef, #e8cfa0); }
  .theme-dot[data-theme="rose"]    { background: linear-gradient(135deg, #faf4f3, #e2bdb8); }
  .theme-dot::after {
    content: attr(data-label); position: absolute; top: 34px; left: 50%;
    transform: translateX(-50%); font-size: 10px; color: var(--text-muted);
    white-space: nowrap; opacity: 0; transition: opacity var(--transition);
    pointer-events: none;
  }
  .theme-dot:hover::after { opacity: 1; }

  /* ======= Persona Switcher ======= */
  .persona-bar {
    display: flex; align-items: center; justify-content: center; gap: 6px;
    padding: 2px 0 16px; flex-wrap: wrap;
  }
  .persona-bar-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    color: var(--text-muted); text-transform: uppercase; margin-right: 4px;
  }
  .persona-cards { display: flex; gap: 5px; flex-wrap: wrap; justify-content: center; }
  .persona-card-mini {
    display: flex; align-items: center; gap: 5px;
    padding: 5px 12px; border-radius: 100px; cursor: pointer;
    background: var(--bg-card); border: 1px solid var(--border);
    transition: all var(--transition); user-select: none;
  }
  .persona-card-mini:hover { border-color: var(--accent-dim); transform: translateY(-1px); box-shadow: var(--shadow); }
  .persona-card-mini.active { border-color: var(--accent); background: var(--accent-soft); box-shadow: var(--shadow); }
  .persona-card-avatar { font-size: 18px; line-height: 1; }
  .persona-card-name { font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; }

  /* ======= Hero ======= */
  .hero { text-align: center; padding: 36px 0 32px; position: relative; }
  .hero-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--accent-strong); padding: 5px 14px;
    border: 1px solid var(--accent-soft); border-radius: 100px;
    margin-bottom: 26px;
  }
  .hero-badge::before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: var(--accent-strong); }
  .hero-avatar {
    width: 96px; height: 96px; border-radius: 50%;
    background: linear-gradient(135deg, var(--accent-soft), var(--bg-soft));
    border: 2px solid var(--border); display: flex; align-items: center; justify-content: center;
    font-size: 46px; margin: 0 auto 18px; box-shadow: var(--shadow);
  }
  .hero h1 {
    font-size: 30px; font-weight: 700; letter-spacing: -0.5px; color: var(--text-primary);
    line-height: 1.2;
  }
  .hero .meta {
    font-size: 14px; color: var(--text-secondary); margin-top: 6px;
    display: flex; align-items: center; justify-content: center; gap: 14px;
  }
  .hero .meta .sep { color: var(--text-muted); font-weight: 300; }

  /* Stat bar */
  .stat-row {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 0;
    margin: 24px 0 0; border-radius: var(--radius);
    background: var(--stat-bg); border: 1px solid var(--border-light);
    overflow: hidden;
  }
  .stat-item { text-align: center; padding: 16px 8px; }
  .stat-value { font-size: 20px; font-weight: 700; color: var(--accent-strong); letter-spacing: -0.3px; }
  .stat-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; font-weight: 500; letter-spacing: 0.04em; }

  /* Tags */
  .tag-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 18px; }
  .tag {
    font-size: 12px; padding: 5px 13px; border-radius: 100px;
    background: var(--tag-bg); border: 1px solid var(--tag-border);
    color: var(--text-secondary); transition: all var(--transition); font-weight: 500;
  }
  .tag:hover { border-color: var(--accent-soft); color: var(--accent-strong); }

  /* ======= Cards ======= */
  .card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 28px;
    box-shadow: var(--shadow); margin-bottom: 14px;
    transition: box-shadow var(--transition), border-color var(--transition);
  }
  .card:hover { box-shadow: var(--shadow-hover); }
  .card-label {
    font-size: 11px; font-weight: 700; letter-spacing: 0.10em; text-transform: uppercase;
    color: var(--text-muted); margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }
  .card-label::before { content: ''; width: 3px; height: 13px; border-radius: 2px; background: var(--accent); }

  /* ======= Input ======= */
  .input-group { display: flex; gap: 10px; }
  .input-group input {
    flex: 1; padding: 13px 18px;
    background: var(--input-bg); border: 1px solid var(--input-border);
    border-radius: var(--radius); font-size: 15px; color: var(--text-primary);
    outline: none; transition: all var(--transition); font-family: inherit;
  }
  .input-group input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
  .input-group input::placeholder { color: var(--text-muted); }
  .input-group input.error { border-color: #d97070; box-shadow: 0 0 0 3px rgba(217,112,112,0.12); }

  .btn {
    padding: 13px 30px;
    background: var(--accent-strong); color: #fff; border: none;
    border-radius: var(--radius); font-size: 15px; font-weight: 600;
    cursor: pointer; transition: all var(--transition); white-space: nowrap;
    font-family: inherit; letter-spacing: -0.1px;
  }
  .btn:hover { filter: brightness(1.08); transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,0.10); }
  .btn:active { transform: translateY(0); filter: brightness(0.95); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; filter: none; }

  /* Quick prompts */
  .quick-section { margin-top: 14px; }
  .quick-label { font-size: 11px; color: var(--text-muted); font-weight: 500; margin-bottom: 8px; letter-spacing: 0.03em; }
  .chips { display: flex; flex-wrap: wrap; gap: 7px; }
  .chip {
    font-size: 13px; padding: 6px 15px; border-radius: 100px;
    background: var(--tag-bg); border: 1px solid var(--tag-border);
    color: var(--text-secondary); cursor: pointer; transition: all var(--transition);
    white-space: nowrap; font-weight: 500;
  }
  .chip:hover { background: var(--accent-soft); border-color: var(--accent-dim); color: var(--accent-strong); }

  /* ======= Answer ======= */
  .answer-body {
    font-size: 16px; line-height: 1.9; color: var(--text-secondary);
    min-height: 56px; transition: all 0.35s; font-weight: 400;
  }
  .answer-body.is-placeholder { color: var(--text-muted); text-align: center; padding: 24px 0; font-style: italic; font-weight: 400; }
  .answer-body.has-content { color: var(--text-primary); font-weight: 400; }

  .answer-meta {
    display: flex; align-items: center; gap: 10px; margin-top: 16px; padding-top: 12px;
    border-top: 1px solid var(--border-light);
  }
  .mode-badge {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 100px;
  }
  .mode-badge.api { background: #eaf7ea; color: #3d8b40; }
  .mode-badge.mock { background: var(--accent-soft); color: var(--accent-strong); }
  .answer-time { font-size: 11px; color: var(--text-muted); font-weight: 500; }

  /* Loading */
  .loading-ring { display: flex; align-items: center; justify-content: center; padding: 28px 0; }
  .loading-ring .ring { width: 30px; height: 30px; border-radius: 50%; border: 2px solid var(--border); border-top-color: var(--accent); animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ======= Diagnostics ======= */
  .diag-card {
    background: var(--bg-card); border: 1px solid var(--border-light);
    border-radius: var(--radius); padding: 16px 20px; margin-top: 14px;
    box-shadow: var(--shadow);
  }
  .diag-card summary {
    font-size: 12px; font-weight: 700; letter-spacing: 0.06em; color: var(--text-muted);
    cursor: pointer; list-style: none; display: flex; align-items: center; gap: 6px;
    user-select: none;
  }
  .diag-card summary::-webkit-details-marker { display: none; }
  .diag-card summary::after { content: '展开'; font-size: 10px; color: var(--accent-dim); margin-left: auto; font-weight: 500; }
  .diag-card details[open] summary::after { content: '收起'; }
  .diag-list { margin-top: 12px; display: flex; flex-direction: column; gap: 7px; }
  .diag-item {
    font-size: 13px; padding: 10px 14px; background: var(--bg-soft);
    border-radius: var(--radius-sm); color: var(--text-secondary); line-height: 1.65;
  }
  .diag-item strong { color: var(--accent-strong); font-weight: 600; }
  .diag-item code { color: var(--accent-strong); background: var(--accent-soft); padding: 1px 5px; border-radius: 3px; font-size: 12px; }
  .diag-note { font-size: 12px; color: var(--text-muted); margin-top: 10px; line-height: 1.6; }
  .diag-note code { color: var(--accent-dim); background: var(--accent-soft); padding: 1px 5px; border-radius: 3px; }

  .footer { text-align: center; padding: 32px 0 0; font-size: 11px; color: var(--text-muted); letter-spacing: 0.04em; font-weight: 500; }

  /* ======= Conversation Thread ======= */
  .conv-thread { display: flex; flex-direction: column; gap: 12px; margin-bottom: 14px; }
  .msg-pair { animation: fadeIn 0.35s ease-out; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  .msg-q {
    background: var(--bg-soft); border: 1px solid var(--border-light);
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg);
    padding: 13px 18px; font-size: 14px; color: var(--text-secondary); font-weight: 500;
    margin-bottom: 8px; position: relative;
  }
  .msg-q::before { content: 'Q'; position: absolute; top: -8px; left: 14px; font-size: 10px; font-weight: 700; color: var(--accent-strong); background: var(--bg-card); padding: 0 6px; letter-spacing: 0.06em; }
  .msg-a {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm);
    padding: 16px 18px; font-size: 15px; line-height: 1.85; color: var(--text-primary);
    position: relative;
  }
  .msg-a::before { content: 'A'; position: absolute; top: -8px; left: 14px; font-size: 10px; font-weight: 700; color: var(--accent); background: var(--bg-card); padding: 0 6px; letter-spacing: 0.06em; }

  /* Sentiment badge */
  .sentiment-badge {
    display: inline-flex; align-items: center; gap: 3px; font-size: 12px; font-weight: 600;
    padding: 3px 10px; border-radius: 100px; margin-top: 8px;
  }
  .sentiment-badge.s-种草 { background: #e8f5e9; color: #2e7d32; }
  .sentiment-badge.s-中立 { background: #f5f5f5; color: #616161; }
  .sentiment-badge.s-吐槽 { background: #fce4ec; color: #c62828; }

  /* Follow-up chips */
  .fu-section { margin-top: 10px; }
  .fu-label { font-size: 10px; font-weight: 700; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 6px; text-transform: uppercase; }
  .fu-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .fu-chip {
    font-size: 12px; padding: 6px 14px; border-radius: 100px; cursor: pointer;
    background: var(--accent-soft); border: 1px solid var(--accent-dim);
    color: var(--accent-strong); font-weight: 500; transition: all var(--transition);
    white-space: nowrap;
  }
  .fu-chip:hover { background: var(--accent-dim); border-color: var(--accent-strong); }

  /* Sentiment Tracker */
  .tracker-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 14px 18px; margin-top: 4px;
    display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  }
  .tracker-title { font-size: 10px; font-weight: 700; letter-spacing: 0.08em; color: var(--text-muted); text-transform: uppercase; }
  .tracker-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; flex: 1; min-width: 120px; background: #eee; }
  .tracker-seg { transition: width 0.4s ease; }
  .tracker-seg.pos { background: #66bb6a; }
  .tracker-seg.neu { background: #bdbdbd; }
  .tracker-seg.neg { background: #ef5350; }
  .tracker-count { font-size: 11px; color: var(--text-muted); font-weight: 500; }

  /* Scenario section */
  .scenario-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 14px; }
  .scenario-card {
    font-size: 12px; padding: 11px 14px; cursor: pointer; border-radius: var(--radius);
    background: var(--bg-card); border: 1px dashed var(--accent-dim);
    color: var(--text-secondary); transition: all var(--transition); line-height: 1.5;
    text-align: left;
  }
  .scenario-card:hover { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-strong); }
  .scenario-card .sc-emoji { font-size: 16px; margin-right: 4px; }

  /* Clear button */
  .btn-clear {
    font-size: 11px; padding: 6px 14px; border-radius: 100px; cursor: pointer;
    background: transparent; border: 1px solid var(--border); color: var(--text-muted);
    transition: all var(--transition); font-family: inherit; font-weight: 500;
    margin-left: auto;
  }
  .btn-clear:hover { border-color: #d97070; color: #d97070; background: rgba(217,112,112,0.04); }

  /* ======= Responsive ======= */
  @media (max-width: 560px) {
    .container { padding: 20px 16px 40px; }
    .input-group { flex-direction: column; }
    .btn { width: 100%; text-align: center; }
    .hero h1 { font-size: 26px; }
    .hero-avatar { width: 80px; height: 80px; font-size: 38px; }
  }
</style>
</head>
<body data-theme="apricot">
<div class="bg-orb orb-1"></div>
<div class="bg-orb orb-2"></div>

<div class="container">
  <!-- Theme Switcher -->
  <div class="theme-bar">
    <span class="theme-label">Theme</span>
    <span class="theme-dot active" data-theme="apricot" data-label="暖杏" onclick="setTheme('apricot')"></span>
    <span class="theme-dot" data-theme="peach" data-label="蜜桃" onclick="setTheme('peach')"></span>
    <span class="theme-dot" data-theme="oat" data-label="燕麦" onclick="setTheme('oat')"></span>
    <span class="theme-dot" data-theme="amber" data-label="琥珀" onclick="setTheme('amber')"></span>
    <span class="theme-dot" data-theme="rose" data-label="玫瑰" onclick="setTheme('rose')"></span>
  </div>

  <!-- Persona Switcher -->
  <div class="persona-bar" id="personaBar"></div>

  <!-- Hero + Persona (dynamic) -->
  <div class="hero" id="heroSection">
    <div class="hero-badge">AI Consumer Simulation</div>
    <div class="hero-avatar" id="heroAvatar"></div>
    <h1 id="heroName"></h1>
    <div class="meta" id="heroMeta"></div>
    <div class="stat-row" id="heroStats"></div>
    <div class="tag-row" id="heroTags"></div>
  </div>

  <!-- Scenario Section -->
  <div id="scenarioSection" style="display:none;">
    <div class="card-label" style="margin-bottom:8px;">What-If Scenarios</div>
    <div class="scenario-grid" id="scenarioGrid"></div>
  </div>

  <!-- Conversation Thread -->
  <div class="conv-thread" id="convThread"></div>

  <!-- Question Input -->
  <div class="card">
    <div class="card-label" style="display:flex;align-items:center;justify-content:space-between;">
      <span>Survey Question</span>
      <button class="btn-clear" id="btnClear" onclick="clearConversation()" style="display:none;">Clear All</button>
    </div>
    <div class="input-group">
      <input id="question" type="text"
             placeholder="输入你想调研的问题..."
             autocomplete="off" maxlength="200">
      <button class="btn" id="submitBtn" onclick="submitQuestion()">
        <span id="btnLabel">提交调研</span>
      </button>
    </div>
    <div class="quick-section">
      <div class="quick-label">Quick Prompts</div>
      <div class="chips" id="quickChips"></div>
    </div>
  </div>

  <!-- Sentiment Tracker -->
  <div class="tracker-card" id="trackerCard" style="display:none;">
    <span class="tracker-title">Sentiment Trend</span>
    <div class="tracker-bar" id="trackerBar"><div class="tracker-seg neu" style="width:100%;"></div></div>
    <span class="tracker-count" id="trackerCount">0 answers</span>
  </div>

  <!-- Diagnostics -->
  <div class="diag-card">
    <details>
      <summary>Test Cases &amp; Diagnostics</summary>
      <div class="diag-list">
        <div class="diag-item"><strong>对话流测试</strong> &mdash; 连续问3个问题，验证追问按钮生成和情感累积</div>
        <div class="diag-item"><strong>场景测试</strong> &mdash; 点击 What-If 场景卡，验证"如果...会怎样"的回答</div>
        <div class="diag-item"><strong>情感追踪</strong> &mdash; 验证每条回答旁显示😊/😐/😠标签，底部追蹤条更新</div>
        <div class="diag-item"><strong>智能追问</strong> &mdash; 点击回答下方的追问按钮，验证对话连续进行</div>
      </div>
      <div class="diag-note">
        &#9432; 运行模式：<strong>{{ 'Claude API' if api_available else 'Mock Engine（内置回答库）' }}</strong>
        {% if not api_available %}&mdash; 设置 <code>ANTHROPIC_API_KEY</code> 后切换真实 AI{% endif %}
      </div>
    </details>
  </div>

  <div class="footer">Mini Consumer Survey Platform &mdash; For Demonstration Only</div>
</div>

<script>
  // ===== DATA =====
  var PERSONAS = {{ personas_json | safe }};
  var DEFAULT_PERSONA = '{{ default_persona }}';
  var currentPersonaId = DEFAULT_PERSONA;
  var conversation = [];
  var sentimentHistory = [];

  // ===== THEME =====
  function setTheme(name) {
    document.body.setAttribute('data-theme', name);
    localStorage.setItem('survey-theme', name);
    document.querySelectorAll('.theme-dot').forEach(function(d) {
      d.classList.toggle('active', d.getAttribute('data-theme') === name);
    });
  }
  (function() {
    var saved = localStorage.getItem('survey-theme');
    if (saved) setTheme(saved);
  })();

  // ===== PERSONA =====
  function switchPersona(id) {
    currentPersonaId = id;
    localStorage.setItem('survey-persona', id);
    renderPersonaBar();
    renderHero();
    renderQuickPrompts();
    fetchScenarios();
  }

  function renderPersonaBar() {
    var bar = document.getElementById('personaBar');
    var html = '<span class="persona-bar-label">Persona</span><div class="persona-cards">';
    for (var pid in PERSONAS) {
      var p = PERSONAS[pid];
      var active = pid === currentPersonaId ? ' active' : '';
      html += '<div class="persona-card-mini' + active + '" onclick="switchPersona(\'' + pid + '\')">';
      html += '<span class="persona-card-avatar">' + p.avatar + '</span>';
      html += '<span class="persona-card-name">' + p.name + '</span></div>';
    }
    html += '</div>';
    bar.innerHTML = html;
  }

  function renderHero() {
    var p = PERSONAS[currentPersonaId];
    document.getElementById('heroAvatar').innerHTML = p.avatar;
    document.getElementById('heroName').textContent = p.name;
    document.getElementById('heroMeta').innerHTML =
      '<span>' + p.age + '</span><span class="sep">|</span>' +
      '<span>' + p.city + '</span><span class="sep">|</span>' +
      '<span>' + p.job + '</span>';
    var sHtml = '';
    p.stats.forEach(function(s) {
      sHtml += '<div class="stat-item"><div class="stat-value">' + s.value + '</div><div class="stat-label">' + s.label + '</div></div>';
    });
    document.getElementById('heroStats').innerHTML = sHtml;
    var tHtml = '';
    p.tags.forEach(function(t) { tHtml += '<span class="tag">' + t + '</span>'; });
    document.getElementById('heroTags').innerHTML = tHtml;
  }

  function renderQuickPrompts() {
    var p = PERSONAS[currentPersonaId];
    var chipsHtml = '';
    p.quick_prompts.forEach(function(qp) {
      chipsHtml += '<span class="chip" onclick="setQuestion(\'' + qp[0].replace(/'/g, "\\'") + '\')">' + qp[1] + '</span>';
    });
    document.getElementById('quickChips').innerHTML = chipsHtml;
  }

  // ===== SCENARIOS =====
  async function fetchScenarios() {
    try {
      var resp = await fetch('/api/scenarios?persona=' + currentPersonaId);
      var data = await resp.json();
      var grid = document.getElementById('scenarioGrid');
      var section = document.getElementById('scenarioSection');
      if (!data.scenarios || data.scenarios.length === 0) { section.style.display = 'none'; return; }
      section.style.display = 'block';
      var emojis = ['🔮','💡','⚡','🎯'];
      var html = '';
      data.scenarios.forEach(function(s, i) {
        html += '<div class="scenario-card" onclick="setQuestion(\'' + s[0].replace(/'/g, "\\'") + '\');submitQuestion();">';
        html += '<span class="sc-emoji">' + (emojis[i] || '❓') + '</span> ' + s[0];
        html += '</div>';
      });
      grid.innerHTML = html;
    } catch(e) { console.log('Scenarios fetch failed'); }
  }

  // ===== CONVERSATION =====
  function renderConversation() {
    var thread = document.getElementById('convThread');
    var clearBtn = document.getElementById('btnClear');
    if (conversation.length === 0) {
      thread.innerHTML = '';
      clearBtn.style.display = 'none';
      return;
    }
    clearBtn.style.display = 'inline-block';
    var html = '';
    conversation.forEach(function(pair, idx) {
      html += '<div class="msg-pair">';
      html += '<div class="msg-q">' + escapeHtml(pair.q) + '</div>';
      html += '<div class="msg-a">' + escapeHtml(pair.a);
      html += '<div class="sentiment-badge s-' + pair.sentiment + '">';
      html += (pair.sentiment === '种草' ? '😊 ' : pair.sentiment === '吐槽' ? '😠 ' : '😐 ') + pair.sentiment;
      html += '</div>';
      // Follow-up chips
      if (pair.follow_ups && pair.follow_ups.length > 0) {
        html += '<div class="fu-section"><div class="fu-label">Smart Follow-up</div><div class="fu-chips">';
        pair.follow_ups.forEach(function(fu) {
          var label = (fu && fu.label) || (fu && fu.text) || (Array.isArray(fu) ? fu[1] : '') || fu || '';
          var text = (fu && fu.text) || (Array.isArray(fu) ? fu[0] : '') || fu || '';
          if (typeof text === 'string' && text) {
            html += '<span class="fu-chip" onclick="setQuestion(\'' + text.replace(/'/g, "\\'") + '\');submitQuestion();">' + label + '</span>';
          }
        });
        html += '</div></div>';
      }
      html += '</div></div>';
    });
    thread.innerHTML = html;
    thread.scrollTop = thread.scrollHeight;
  }

  function renderTracker() {
    var card = document.getElementById('trackerCard');
    var bar = document.getElementById('trackerBar');
    var countEl = document.getElementById('trackerCount');
    if (sentimentHistory.length === 0) { card.style.display = 'none'; return; }
    card.style.display = 'flex';
    var pos = 0, neu = 0, neg = 0;
    sentimentHistory.forEach(function(s) {
      if (s === '种草') pos++; else if (s === '吐槽') neg++; else neu++;
    });
    var total = sentimentHistory.length;
    var pPct = Math.round(pos/total*100), nPct = Math.round(neu/total*100), gPct = 100-pPct-nPct;
    bar.innerHTML = '<div class="tracker-seg pos" style="width:' + pPct + '%"></div>' +
                    '<div class="tracker-seg neu" style="width:' + nPct + '%"></div>' +
                    '<div class="tracker-seg neg" style="width:' + gPct + '%"></div>';
    countEl.textContent = total + ' answers · ' + pPct + '% 😊 ' + nPct + '% 😐 ' + gPct + '% 😠';
  }

  function clearConversation() {
    conversation = [];
    sentimentHistory = [];
    renderConversation();
    renderTracker();
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ===== INIT =====
  (function() {
    var savedPersona = localStorage.getItem('survey-persona');
    if (PERSONAS[savedPersona]) currentPersonaId = savedPersona;
    renderPersonaBar();
    renderHero();
    renderQuickPrompts();
    fetchScenarios();
    renderConversation();
    renderTracker();
  })();

  // ===== SURVEY =====
  var questionInput = document.getElementById('question');
  var submitBtn = document.getElementById('submitBtn');
  var btnLabel = document.getElementById('btnLabel');
  var loading = false;

  window.setQuestion = function(text) {
    questionInput.value = text;
    questionInput.focus();
  };

  questionInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !loading) submitQuestion();
  });

  async function submitQuestion() {
    var question = questionInput.value.trim();
    if (!question) {
      questionInput.classList.add('error');
      setTimeout(function() { questionInput.classList.remove('error'); }, 1500);
      return;
    }
    if (loading) return;
    loading = true;
    submitBtn.disabled = true;
    btnLabel.textContent = '生成中...';

    try {
      var resp = await fetch('/api/survey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question, persona: currentPersonaId })
      });
      var data = await resp.json();
      if (resp.ok) {
        conversation.push({
          q: question, a: data.answer,
          sentiment: data.sentiment || '中立',
          follow_ups: data.follow_ups || []
        });
        sentimentHistory.push(data.sentiment || '中立');
        questionInput.value = '';
      }
    } catch (err) {
      conversation.push({ q: question, a: '网络请求失败，请确认后端已启动', sentiment: '中立', follow_ups: [] });
      sentimentHistory.push('中立');
    }

    renderConversation();
    renderTracker();
    loading = false;
    submitBtn.disabled = false;
    btnLabel.textContent = '提交调研';
  }
</script>
</body>
</html>"""


@app.route("/")
def index():
    # Build persona list for frontend (exclude heavy fields)
    persona_list = {}
    for pid, p in PERSONAS.items():
        persona_list[pid] = {
            "id": p["id"], "name": p["name"], "avatar": p["avatar"],
            "age": p["age"], "city": p["city"], "job": p["job"],
            "stats": p["stats"], "tags": p["tags"], "quick_prompts": p["quick_prompts"],
        }
    return render_template_string(
        HTML, api_available=ANTHROPIC_AVAILABLE,
        personas_json=json.dumps(persona_list, ensure_ascii=False),
        default_persona=DEFAULT_PERSONA,
    )


@app.route("/api/survey", methods=["POST"])
def survey():
    data = request.get_json(silent=True) or {}
    question = (data.get("question", "") or "").strip()
    persona_id = (data.get("persona", "") or DEFAULT_PERSONA).strip()

    if persona_id not in PERSONAS:
        persona_id = DEFAULT_PERSONA
    if not question:
        return jsonify({"error": "请输入调研问题"}), 400
    if len(question) > 200:
        return jsonify({"error": "问题长度不能超过200字"}), 400

    if ANTHROPIC_AVAILABLE:
        try:
            result = call_anthropic(question, persona_id)
            return jsonify({"answer": result["answer"], "sentiment": result["sentiment"],
                           "follow_ups": result["follow_ups"], "mode": "anthropic"})
        except Exception as e:
            print(f"[ERROR] Anthropic API 调用失败: {e}")
            result = mock_answer(question, persona_id)
            return jsonify({"answer": result["answer"], "sentiment": result["sentiment"],
                           "follow_ups": result["follow_ups"], "mode": "mock-fallback"})
    else:
        result = mock_answer(question, persona_id)
        return jsonify({"answer": result["answer"], "sentiment": result["sentiment"],
                       "follow_ups": result["follow_ups"], "mode": "mock"})


@app.route("/api/scenarios")
def scenarios():
    persona_id = request.args.get("persona", DEFAULT_PERSONA).strip()
    if persona_id not in SCENARIOS:
        persona_id = DEFAULT_PERSONA
    return jsonify({"scenarios": SCENARIOS.get(persona_id, [])})


if __name__ == "__main__":
    print("=" * 50)
    print("  迷你模拟消费者调研平台")
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host="127.0.0.1", port=5000)
