# -*- coding: utf-8 -*-
"""成品场景预设。

跟风格维度库的分工：
  风格维度 = 让用户自己配（媒介/流派/光照/镜头/构图/调色/情绪）
  场景预设 = 配好的一套，一键套用，省去逐个维度点选

套用场景预设的行为：
  1. 把它定义的 styles 填进各维度选择器（用户随后可以改其中任何一项）
  2. 把 scaffold 作为输入框的起点（用户往里面加自己的主体）

scaffold 是"场景骨架"而非完整提示词——它只描述环境，
不含主体，因为主体必须由用户提供（这是防跑偏的前提）。

styles 里的 id 必须存在于 styles.py，__main__ 里有校验。
"""

SCENE_PRESETS = [
    # ---------------- 都市夜景 ----------------
    {"id": "neon_rain_street", "zh": "雨夜霓虹街头", "category": "都市夜景",
     "scaffold": "rain-slicked city street at night, neon signs reflecting in puddles",
     "scaffold_zh": "夜晚湿漉漉的城市街道，霓虹招牌倒映在积水中",
     "styles": {"genre": "cyberpunk", "lighting": "neon", "palette": "cyber_cyan_magenta",
                "camera": "wide", "mood": "lonely"},
     "hint": "适合孤独人物、赛博题材"},
    {"id": "rooftop_overlook", "zh": "天台俯瞰都市", "category": "都市夜景",
     "scaffold": "rooftop overlooking a sprawling city at night, distant lights",
     "scaffold_zh": "天台俯瞰夜色中铺展的城市，远处灯火点点",
     "styles": {"genre": "cyberpunk", "lighting": "blue_hour", "camera": "aerial",
                "palette": "cool", "mood": "melancholic"},
     "hint": "俯瞰视角，适合收尾镜头"},
    {"id": "alley_neon", "zh": "窄巷霓虹", "category": "都市夜景",
     "scaffold": "narrow back alley, tangled cables, glowing signs overhead",
     "scaffold_zh": "狭窄后巷，缠绕的线缆，头顶发光的招牌",
     "styles": {"genre": "cyberpunk", "lighting": "neon", "camera": "low_angle",
                "composition": "diagonal", "palette": "neon_clash", "mood": "tense"},
     "hint": "压迫感，适合追逐或对峙"},
    {"id": "rain_window", "zh": "雨夜窗前", "category": "都市夜景",
     "scaffold": "rain running down a window, blurred city lights beyond the glass",
     "scaffold_zh": "雨水顺着窗户流下，玻璃外是模糊的城市灯火",
     "styles": {"lighting": "screen_glow", "camera": "closeup", "palette": "cyber_cyan_magenta",
                "mood": "melancholic", "medium": "film_photo"},
     "hint": "室内视角，适合情绪特写"},
    {"id": "subway_platform", "zh": "深夜地铁站", "category": "都市夜景",
     "scaffold": "empty subway platform late at night, fluorescent tubes overhead",
     "scaffold_zh": "深夜空旷的地铁站台，头顶是一排荧光灯管",
     "styles": {"lighting": "fluorescent", "camera": "wide", "palette": "desaturated",
                "composition": "leading_lines", "mood": "oppressive"},
     "hint": "空寂感，荧光灯的冷绿特别出味"},
    {"id": "parking_garage", "zh": "地下车库", "category": "都市夜景",
     "scaffold": "underground parking garage, concrete pillars, single working lamp",
     "scaffold_zh": "地下车库，混凝土立柱，只有一盏亮着的灯",
     "styles": {"lighting": "spotlight", "camera": "wide", "palette": "crimson_black",
                "mood": "foreboding", "medium": "photography"},
     "hint": "悬疑感，红黑对比"},
    {"id": "traffic_long_exposure", "zh": "长曝光车流", "category": "都市夜景",
     "scaffold": "city intersection at night, traffic light trails streaking past",
     "scaffold_zh": "夜晚的城市十字路口，车灯光轨划过画面",
     "styles": {"lighting": "headlights", "camera": "long_exposure", "palette": "teal_orange",
                "mood": "epic", "medium": "photography"},
     "hint": "长时间曝光，光轨是主体"},
    {"id": "tokyo_crossing", "zh": "涩谷十字路口", "category": "都市夜景",
     "scaffold": "cramped pedestrian crossing packed with people, walls of signage",
     "scaffold_zh": "拥挤的人行横道，人潮密集，四周是招牌墙",
     "styles": {"genre": "cyberpunk", "lighting": "neon", "camera": "high_angle",
                "palette": "saturated", "mood": "frenzied"},
     "hint": "高密度人群，俯拍"},

    # ---------------- 自然风景 ----------------
    {"id": "ghibli_meadow", "zh": "吉卜力夏日草原", "category": "自然风景",
     "scaffold": "rolling summer meadow under towering cumulus clouds",
     "scaffold_zh": "夏日起伏的草原，头顶是高耸的积云",
     "styles": {"genre": "ghibli", "lighting": "golden_hour", "camera": "wide",
                "palette": "spring", "mood": "serene", "medium": "cel"},
     "hint": "经典吉卜力，云是主角"},
    {"id": "misty_forest", "zh": "晨雾森林", "category": "自然风景",
     "scaffold": "dense forest at dawn, fog drifting between the trunks",
     "scaffold_zh": "黎明时分的密林，雾气在树干之间流动",
     "styles": {"lighting": "volumetric", "camera": "medium_shot", "palette": "earthy",
                "composition": "leading_lines", "mood": "mysterious"},
     "hint": "体积光是关键"},
    {"id": "autumn_lake", "zh": "秋日湖畔", "category": "自然风景",
     "scaffold": "still lake at the edge of an autumn forest, perfect reflection",
     "scaffold_zh": "秋日森林边的静谧湖面，完美的倒影",
     "styles": {"lighting": "golden_hour", "camera": "wide", "palette": "autumn",
                "composition": "bilateral", "mood": "serene", "medium": "photography"},
     "hint": "对称倒影构图"},
    {"id": "desert_dunes", "zh": "沙漠沙丘", "category": "自然风景",
     "scaffold": "vast sand dunes, wind-carved ridgelines, empty horizon",
     "scaffold_zh": "广袤的沙丘，风蚀出的脊线，空旷的地平线",
     "styles": {"lighting": "sunset", "camera": "ultrawide", "palette": "warm",
                "composition": "low_horizon", "mood": "epic"},
     "hint": "极简，线条感强"},
    {"id": "storm_ocean", "zh": "暴风雨海面", "category": "自然风景",
     "scaffold": "open ocean under a black storm front, heavy swell",
     "scaffold_zh": "黑色风暴锋面下的开阔海面，汹涌的涌浪",
     "styles": {"lighting": "lightning", "camera": "wide", "palette": "winter",
                "mood": "foreboding", "genre": "romanticism"},
     "hint": "浪漫主义式的崇高感"},
    {"id": "snow_mountain", "zh": "雪山", "category": "自然风景",
     "scaffold": "snow-covered mountain range, sharp peaks against a pale sky",
     "scaffold_zh": "覆雪的山脉，锐利的峰尖衬着苍白的天空",
     "styles": {"lighting": "noon", "camera": "ultrawide", "palette": "winter",
                "mood": "epic", "medium": "large_format"},
     "hint": "大画幅质感，细节拉满"},
    {"id": "northern_lights", "zh": "极光", "category": "自然风景",
     "scaffold": "aurora ribbons across a star-filled sky above a frozen lake",
     "scaffold_zh": "结冰的湖面上方，极光丝带横贯星空",
     "styles": {"lighting": "moonlight", "camera": "long_exposure", "palette": "cool",
                "mood": "sacred", "medium": "photography"},
     "hint": "长曝光，极光是主光源"},
    {"id": "japanese_spring", "zh": "春季樱花", "category": "自然风景",
     "scaffold": "cherry blossom branches in full bloom, petals drifting",
     "scaffold_zh": "盛开的樱花枝，花瓣正在飘落",
     "styles": {"genre": "shinkai", "lighting": "backlit", "camera": "closeup",
                "palette": "pastel", "mood": "nostalgic"},
     "hint": "逆光花瓣，新海诚式"},
    {"id": "cliff_coast", "zh": "海崖海岸", "category": "自然风景",
     "scaffold": "sheer coastal cliffs meeting rough surf, spray at the base",
     "scaffold_zh": "陡峭的海崖与汹涌浪花相接，崖底腾起水雾",
     "styles": {"lighting": "overcast", "camera": "aerial", "palette": "cool",
                "mood": "stoic", "medium": "photography"},
     "hint": "阴天的灰调最出质感"},
    {"id": "ink_wash_mountain", "zh": "水墨山水", "category": "自然风景",
     "scaffold": "layered mountain ridges receding into mist",
     "scaffold_zh": "层叠的山峦没入雾中",
     "styles": {"medium": "ink_wash", "palette": "monochrome", "composition": "negative_space",
                "camera": "ultrawide", "mood": "serene"},
     "hint": "留白是构图的一部分"},

    # ---------------- 人物肖像 ----------------
    {"id": "editorial_portrait", "zh": "时尚杂志肖像", "category": "人物肖像",
     "scaffold": "studio portrait against a seamless backdrop",
     "scaffold_zh": "棚拍肖像，无缝背景",
     "styles": {"lighting": "softbox", "camera": "medium_shot", "palette": "morandi",
                "mood": "stoic", "medium": "photography"},
     "hint": "干净背景，重点在光"},
    {"id": "rembrandt_study", "zh": "伦勃朗光肖像", "category": "人物肖像",
     "scaffold": "classical portrait study, dark background",
     "scaffold_zh": "古典肖像习作，深色背景",
     "styles": {"lighting": "rembrandt", "camera": "closeup", "palette": "sepia",
                "composition": "thirds", "genre": "renaissance"},
     "hint": "单侧打光，脸颊三角高光"},
    {"id": "film_noir_portrait", "zh": "黑色电影特写", "category": "人物肖像",
     "scaffold": "hard-shadowed portrait in a dim room, blind slats casting stripes",
     "scaffold_zh": "昏暗房间里硬阴影的肖像，百叶窗投下条纹光",
     "styles": {"lighting": "chiaroscuro", "camera": "closeup", "palette": "bw",
                "mood": "tense", "medium": "film_photo"},
     "hint": "百叶窗阴影是标志"},
    {"id": "oil_portrait", "zh": "古典油画肖像", "category": "人物肖像",
     "scaffold": "formal portrait in the manner of old master painting",
     "scaffold_zh": "古典大师油画风格的正式肖像",
     "styles": {"medium": "oil", "lighting": "chiaroscuro", "genre": "baroque",
                "palette": "gold_blue", "mood": "sacred"},
     "hint": "厚涂 + 明暗对照"},
    {"id": "backlit_silhouette", "zh": "逆光剪影", "category": "人物肖像",
     "scaffold": "backlit silhouette against a bright open background",
     "scaffold_zh": "明亮开阔背景前的逆光剪影",
     "styles": {"lighting": "backlit", "camera": "medium_shot", "palette": "warm",
                "composition": "negative_space", "mood": "lonely"},
     "hint": "看不到脸，靠轮廓说话"},
    {"id": "rain_portrait", "zh": "雨中人像", "category": "人物肖像",
     "scaffold": "person standing in heavy rain, water beading on skin",
     "scaffold_zh": "站在大雨中的人，水珠挂在皮肤上",
     "styles": {"lighting": "neon", "camera": "closeup", "palette": "cyber_cyan_magenta",
                "mood": "melancholic", "medium": "photography"},
     "hint": "霓虹打在水珠上"},
    {"id": "window_light_portrait", "zh": "窗光肖像", "category": "人物肖像",
     "scaffold": "soft window light falling across a quiet interior",
     "scaffold_zh": "柔和的窗光洒进安静的室内",
     "styles": {"lighting": "sidelight", "camera": "closeup", "palette": "pastel",
                "mood": "intimate", "medium": "photography"},
     "hint": "柔和的单侧窗光"},
    {"id": "low_angle_hero", "zh": "仰视英雄", "category": "人物肖像",
     "scaffold": "imposing figure seen from below against a dramatic sky",
     "scaffold_zh": "戏剧性天空下仰视的伟岸身影",
     "styles": {"lighting": "rim", "camera": "low_angle", "palette": "saturated",
                "mood": "epic", "genre": "superhero"},
     "hint": "仰拍 + 轮廓光"},
    {"id": "victorian_portrait", "zh": "维多利亚肖像", "category": "人物肖像",
     "scaffold": "somber formal portrait, period costume, muted interior",
     "scaffold_zh": "沉郁的正式肖像，时代服装，柔和的室内",
     "styles": {"medium": "photography", "palette": "sepia", "genre": "gothic",
                "lighting": "sidelight", "mood": "stoic"},
     "hint": "哥特调性的复古肖像"},
    {"id": "anime_closeup", "zh": "动画特写", "category": "人物肖像",
     "scaffold": "expressive close-up, wind moving through hair",
     "scaffold_zh": "富有表现力的特写，风吹过发丝",
     "styles": {"genre": "shinkai", "medium": "cel", "lighting": "rim",
                "camera": "closeup", "palette": "saturated", "mood": "joyful"},
     "hint": "赛璐璐 + 轮廓光"},

    # ---------------- 奇幻科幻 ----------------
    {"id": "cyberpunk_market", "zh": "赛博朋克市集", "category": "奇幻科幻",
     "scaffold": "crowded night market under layered awnings and hanging cables",
     "scaffold_zh": "拥挤的夜市，层叠的雨棚与垂落的线缆",
     "styles": {"genre": "cyberpunk", "lighting": "neon", "camera": "wide",
                "palette": "neon_clash", "mood": "frenzied"},
     "hint": "高密度信息量"},
    {"id": "space_station", "zh": "空间站舷窗", "category": "奇幻科幻",
     "scaffold": "interior of an orbital station, planet visible through the viewport",
     "scaffold_zh": "轨道站内部，舷窗外可见行星",
     "styles": {"genre": "retro_scifi", "lighting": "screen_glow", "camera": "medium_shot",
                "palette": "cool", "mood": "lonely"},
     "hint": "复古科幻的仪表盘味道"},
    {"id": "mech_bay", "zh": "机甲整备库", "category": "奇幻科幻",
     "scaffold": "industrial hangar, towering machine under maintenance lights",
     "scaffold_zh": "工业机库，巨大的机械停在检修灯下",
     "styles": {"genre": "dieselpunk", "lighting": "spotlight", "camera": "low_angle",
                "palette": "earthy", "mood": "epic"},
     "hint": "工业感，体积对比强烈"},
    {"id": "fantasy_castle", "zh": "奇幻城堡", "category": "奇幻科幻",
     "scaffold": "spired castle on a cliff, banners in the wind",
     "scaffold_zh": "悬崖上的尖塔城堡，旗帜在风中",
     "styles": {"genre": "medieval_fantasy", "lighting": "sunset", "camera": "wide",
                "palette": "jewel", "mood": "epic", "medium": "oil"},
     "hint": "古典油画质感"},
    {"id": "dark_ritual", "zh": "黑暗仪式", "category": "奇幻科幻",
     "scaffold": "candlelit stone chamber, symbols carved into the floor",
     "scaffold_zh": "烛光照亮的石室，地面刻着符号",
     "styles": {"genre": "dark_fantasy", "lighting": "candlelight", "camera": "high_angle",
                "palette": "crimson_black", "mood": "foreboding"},
     "hint": "烛光 + 俯拍"},
    {"id": "eldritch_entity", "zh": "不可名状之物", "category": "奇幻科幻",
     "scaffold": "vast incomprehensible form rising beyond the horizon",
     "scaffold_zh": "地平线之外升起的、不可名状的巨大形体",
     "styles": {"genre": "cosmic_horror", "lighting": "overcast", "camera": "ultrawide",
                "palette": "desaturated", "mood": "apocalyptic"},
     "hint": "尺度对比是关键"},
    {"id": "solarpunk_city", "zh": "太阳朋克城市", "category": "奇幻科幻",
     "scaffold": "terraced green city, glass facades overgrown with vegetation",
     "scaffold_zh": "梯田式的绿色城市，玻璃幕墙爬满植被",
     "styles": {"genre": "solarpunk", "lighting": "golden_hour", "camera": "drone",
                "palette": "spring", "mood": "healing"},
     "hint": "明亮乐观的未来"},
    {"id": "wasteland_scavenger", "zh": "废土拾荒", "category": "奇幻科幻",
     "scaffold": "ruined highway strewn with rusted wrecks, dust haze",
     "scaffold_zh": "废弃公路散落着锈蚀残骸，沙尘弥漫",
     "styles": {"genre": "wasteland", "lighting": "noon", "camera": "wide",
                "palette": "earthy", "mood": "stoic"},
     "hint": "正午硬光最出废土感"},
    {"id": "underwater_ruins", "zh": "水下遗迹", "category": "奇幻科幻",
     "scaffold": "submerged stone ruins, shafts of light from the surface",
     "scaffold_zh": "淹没在水下的石造遗迹，阳光从水面射下",
     "styles": {"lighting": "caustics", "camera": "wide", "palette": "cool",
                "mood": "mysterious", "medium": "photography"},
     "hint": "焦散光纹是灵魂"},
    {"id": "cyber_samurai", "zh": "赛博武士", "category": "奇幻科幻",
     "scaffold": "lone figure in traditional armor with cybernetic augmentation",
     "scaffold_zh": "身着传统铠甲、带义体改造的孤影",
     "styles": {"genre": "silkpunk", "lighting": "neon", "camera": "medium_shot",
                "palette": "gold_blue", "mood": "stoic"},
     "hint": "传统与未来对撞"},

    # ---------------- 恐怖悬疑 ----------------
    {"id": "abandoned_hospital", "zh": "废弃医院", "category": "恐怖悬疑",
     "scaffold": "abandoned hospital corridor, peeling paint, gurney in the dark",
     "scaffold_zh": "废弃的医院走廊，剥落的墙皮，黑暗中的担架车",
     "styles": {"genre": "j_horror", "lighting": "fluorescent", "camera": "wide",
                "palette": "desaturated", "mood": "oppressive"},
     "hint": "荧光灯 + 长廊透视"},
    {"id": "foggy_road", "zh": "雾中公路", "category": "恐怖悬疑",
     "scaffold": "empty rural road swallowed by fog, single pair of headlights",
     "scaffold_zh": "被浓雾吞没的乡间公路，只有一对车灯",
     "styles": {"lighting": "headlights", "camera": "wide", "palette": "cool",
                "mood": "foreboding", "genre": "j_horror"},
     "hint": "看不见的东西最吓人"},
    {"id": "creepy_doll", "zh": "诡异玩偶", "category": "恐怖悬疑",
     "scaffold": "antique doll propped in a dusty chair, dim room",
     "scaffold_zh": "古董玩偶靠在积灰的椅子上，昏暗的房间",
     "styles": {"lighting": "underlight", "camera": "closeup", "palette": "sepia",
                "mood": "foreboding", "medium": "photography"},
     "hint": "底光制造不安"},
    {"id": "shadow_figure", "zh": "门后身影", "category": "恐怖悬疑",
     "scaffold": "dark silhouette barely visible through a cracked doorway",
     "scaffold_zh": "从门缝中隐约可见的黑色身影",
     "styles": {"lighting": "backlit", "camera": "medium_shot", "palette": "monochrome",
                "mood": "tense", "genre": "j_horror"},
     "hint": "只给轮廓，不给细节"},
    {"id": "overgrown_house", "zh": "荒宅", "category": "恐怖悬疑",
     "scaffold": "derelict Victorian house reclaimed by vines",
     "scaffold_zh": "被藤蔓吞没的废弃维多利亚式宅邸",
     "styles": {"genre": "gothic", "lighting": "overcast", "camera": "wide",
                "palette": "desaturated", "mood": "melancholic"},
     "hint": "阴天下的哥特建筑"},
    {"id": "ritual_woods", "zh": "林中异象", "category": "恐怖悬疑",
     "scaffold": "clearing in deep woods at night, something hanging between the trees",
     "scaffold_zh": "夜晚密林中的空地，树间悬挂着什么",
     "styles": {"lighting": "moonlight", "camera": "wide", "palette": "cool",
                "mood": "foreboding", "genre": "cosmic_horror"},
     "hint": "月光下的林中空地"},

    # ---------------- 复古怀旧 ----------------
    {"id": "retro_diner", "zh": "复古美式餐厅", "category": "复古怀旧",
     "scaffold": "chrome-and-vinyl diner booth, checkerboard floor",
     "scaffold_zh": "铬合金与皮革的餐厅卡座，棋盘格地板",
     "styles": {"genre": "retro_scifi", "lighting": "neon", "palette": "portra",
                "mood": "nostalgic", "medium": "film_photo"},
     "hint": "50 年代美式，暖调胶片"},
    {"id": "polaroid_summer", "zh": "宝丽来夏日", "category": "复古怀旧",
     "scaffold": "sunlit backyard, overexposed highlights, faded colors",
     "scaffold_zh": "阳光下的后院，过曝的高光，褪色的色彩",
     "styles": {"medium": "film_photo", "palette": "desaturated", "lighting": "noon",
                "mood": "nostalgic", "camera": "medium_shot"},
     "hint": "过曝 + 褪色最有年代感"},
    {"id": "vhs_glitch", "zh": "VHS 故障", "category": "复古怀旧",
     "scaffold": "degraded analog video frame, tracking errors and color bleed",
     "scaffold_zh": "劣化的模拟录像画面，跟踪误差与色彩溢出",
     "styles": {"genre": "vaporwave", "palette": "cyber_cyan_magenta", "lighting": "screen_glow",
                "mood": "dreamlike", "medium": "film_photo"},
     "hint": "模拟信号的失真感"},
    {"id": "70s_film", "zh": "70 年代胶片", "category": "复古怀旧",
     "scaffold": "sun-bleached street scene, heavy grain, warm cast",
     "scaffold_zh": "被阳光晒褪的街景，粗颗粒，暖偏色",
     "styles": {"medium": "film_photo", "palette": "portra", "lighting": "golden_hour",
                "mood": "nostalgic", "camera": "wide"},
     "hint": "颗粒和暖偏色是重点"},
    {"id": "art_deco_poster", "zh": "装饰艺术海报", "category": "复古怀旧",
     "scaffold": "geometric poster composition, streamlined ornament",
     "scaffold_zh": "几何化的海报构图，流线型的装饰",
     "styles": {"genre": "art_deco", "medium": "vector", "palette": "gold_blue",
                "composition": "centered", "mood": "epic"},
     "hint": "对称 + 几何装饰"},
    {"id": "constructivist_poster", "zh": "构成主义海报", "category": "复古怀旧",
     "scaffold": "bold diagonal poster layout, heavy sans-serif blocks",
     "scaffold_zh": "大胆的对角线海报版式，粗重的无衬线色块",
     "styles": {"genre": "constructivism", "medium": "vector", "palette": "crimson_black",
                "composition": "diagonal", "mood": "frenzied"},
     "hint": "红黑 + 对角线冲击"},
    {"id": "sepia_war_photo", "zh": "战地纪实", "category": "复古怀旧",
     "scaffold": "documentary scene, grainy monochrome, harsh available light",
     "scaffold_zh": "纪实场景，颗粒感黑白，严酷的自然光",
     "styles": {"medium": "film_photo", "palette": "bw", "lighting": "hard_light",
                "mood": "stoic", "camera": "medium_shot"},
     "hint": "纪实感，不修边幅"},
    {"id": "ukiyoe_wave", "zh": "浮世绘海浪", "category": "复古怀旧",
     "scaffold": "stylized ocean waves with curling foam claws",
     "scaffold_zh": "风格化的海浪，卷起爪状的泡沫",
     "styles": {"medium": "ukiyoe", "palette": "jewel", "composition": "diagonal",
                "mood": "epic", "camera": "wide"},
     "hint": "平面化处理，装饰性强"},

    # ---------------- 室内静物 ----------------
    {"id": "moody_still_life", "zh": "暗调静物", "category": "室内静物",
     "scaffold": "tabletop arrangement lit by a single side window",
     "scaffold_zh": "桌面上的一组静物，单侧窗光照明",
     "styles": {"medium": "oil", "lighting": "chiaroscuro", "genre": "baroque",
                "camera": "closeup", "palette": "earthy", "mood": "serene"},
     "hint": "古典静物画的路子"},
    {"id": "cozy_reading_nook", "zh": "温暖阅读角", "category": "室内静物",
     "scaffold": "armchair by a window, stacked books, mug still steaming",
     "scaffold_zh": "窗边的扶手椅，堆叠的书，还冒着热气的杯子",
     "styles": {"lighting": "golden_hour", "camera": "medium_shot", "palette": "warm",
                "mood": "healing", "medium": "photography"},
     "hint": "治愈系"},
    {"id": "cyber_workspace", "zh": "赛博工作台", "category": "室内静物",
     "scaffold": "cluttered desk surrounded by monitors and cables, night outside",
     "scaffold_zh": "堆满杂物的书桌，环绕的显示器与线缆，窗外是夜",
     "styles": {"genre": "cyberpunk", "lighting": "screen_glow", "camera": "medium_shot",
                "palette": "cyber_cyan_magenta", "mood": "lonely"},
     "hint": "屏幕光做主光源"},
    {"id": "minimal_interior", "zh": "极简室内", "category": "室内静物",
     "scaffold": "spare room, single chair, hard sunlight on a bare wall",
     "scaffold_zh": "空旷的房间，一把椅子，硬阳光打在光秃的墙上",
     "styles": {"genre": "minimalism", "lighting": "hard_light", "palette": "morandi",
                "composition": "negative_space", "mood": "serene"},
     "hint": "负空间为主"},

    # ---------------- 动画插画 ----------------
    {"id": "ghibli_flight", "zh": "吉卜力飞行", "category": "动画插画",
     "scaffold": "soaring above clouds, wind and open sky",
     "scaffold_zh": "在云层之上翱翔，风与开阔的天空",
     "styles": {"genre": "ghibli", "lighting": "golden_hour", "camera": "wide",
                "palette": "saturated", "mood": "joyful", "medium": "cel"},
     "hint": "吉卜力式飞行镜头"},
    {"id": "shinkai_twilight", "zh": "新海诚黄昏", "category": "动画插画",
     "scaffold": "city skyline at twilight, enormous cloud formations",
     "scaffold_zh": "黄昏的城市天际线，巨大的云层",
     "styles": {"genre": "shinkai", "lighting": "blue_hour", "camera": "wide",
                "palette": "saturated", "mood": "melancholic", "medium": "cel"},
     "hint": "云和天空是主角"},
    {"id": "pixar_character", "zh": "皮克斯角色", "category": "动画插画",
     "scaffold": "appealing character design in a warm interior",
     "scaffold_zh": "温暖室内的讨喜角色设计",
     "styles": {"genre": "pixar", "lighting": "softbox", "camera": "medium_shot",
                "palette": "pastel", "mood": "joyful", "medium": "render3d"},
     "hint": "3D 动画，比例夸张"},
    {"id": "concept_art_env", "zh": "概念设定图", "category": "动画插画",
     "scaffold": "environment concept painting, loose suggestive brushwork",
     "scaffold_zh": "环境概念设定画，放松的暗示性笔触",
     "styles": {"medium": "airbrush", "lighting": "volumetric",
                "camera": "wide", "palette": "earthy", "mood": "epic"},
     "hint": "影视前期设定的画法"},
    {"id": "pixel_scene", "zh": "像素场景", "category": "动画插画",
     "scaffold": "side-scrolling game scene, tile-based environment",
     "scaffold_zh": "横版卷轴游戏场景，瓦片式环境",
     "styles": {"medium": "pixel", "palette": "saturated", "lighting": "sunset",
                "camera": "wide", "mood": "nostalgic"},
     "hint": "限定色板是重点"},
    {"id": "watercolor_storybook", "zh": "水彩绘本", "category": "动画插画",
     "scaffold": "gentle illustrated scene with soft washes and white space",
     "scaffold_zh": "柔和的插画场景，淡雅的水痕与留白",
     "styles": {"medium": "watercolor", "genre": "childrens_book", "palette": "pastel",
                "composition": "negative_space", "mood": "tender"},
     "hint": "留白和水痕"},
]


# ---- 查询辅助 ----------------------------------------------------------

_BY_ID = {p["id"]: p for p in SCENE_PRESETS}


def get(preset_id):
    return _BY_ID.get(preset_id)


def catalog():
    return [
        {
            "id": p["id"],
            "zh": p["zh"],
            "category": p["category"],
            "scaffold": p["scaffold"],
            "scaffold_zh": p["scaffold_zh"],
            "hint": p["hint"],
            "styles": p["styles"],
        }
        for p in SCENE_PRESETS
    ]


def categories():
    seen = []
    for p in SCENE_PRESETS:
        if p["category"] not in seen:
            seen.append(p["category"])
    return seen


def stats():
    return {"presets": len(SCENE_PRESETS), "categories": len(categories())}


if __name__ == "__main__":
    import sys, os, io
    # ComfyUI 的 python_embeded 处于 isolated 模式（存在 python312._pth），
    # 不会把脚本所在目录加入 sys.path，必须手动加。
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    # 校验：所有引用的风格 id 必须存在，且必须属于它被放进的那个维度
    from styles import get_item, STYLE_DIMENSIONS
    valid_dims = {d["key"] for d in STYLE_DIMENSIONS}

    bad = []
    for p in SCENE_PRESETS:
        for dim_key, item_id in p["styles"].items():
            if dim_key not in valid_dims:
                bad.append(f"{p['id']}: 未知维度 '{dim_key}'")
                continue
            item = get_item(item_id)
            if item is None:
                bad.append(f"{p['id']}: 风格 id '{item_id}' 不存在")
            elif item["dimension"] != dim_key:
                bad.append(
                    f"{p['id']}: '{item_id}' 属于 {item['dimension']}，却放在 {dim_key}"
                )

    # 校验：id 不重复
    ids = [p["id"] for p in SCENE_PRESETS]
    dupes = {i for i in ids if ids.count(i) > 1}

    s = stats()
    print(f"场景预设 {s['presets']} 个，分 {s['categories']} 类")
    for c in categories():
        n = sum(1 for p in SCENE_PRESETS if p["category"] == c)
        print(f"  {c:<10} {n:>2} 个")

    if dupes:
        print(f"\n[错误] id 重复: {dupes}")
    if bad:
        print(f"\n[错误] {len(bad)} 处引用问题:")
        for b in bad:
            print(f"  {b}")
    if not bad and not dupes:
        print("\n[通过] 所有风格引用均有效")
    sys.exit(1 if (bad or dupes) else 0)
