# -*- coding: utf-8 -*-
"""风格维度库。

设计约束（针对"模型乱加戏、原话被稀释"的问题）：

  1. 每个词条的 inject 严格控制在 3-8 个英文词。
     旧节点包的 AESTHETIC_DESCRIPTORS 每条是 15-25 词的形容词堆，
     用户点一个风格就自动注入一长串，本身就是膨胀源。这里反着来。

  2. inject 是"唯一允许模型新增的内容"。
     引擎会把它作为白名单写进 system prompt，模型想加戏只能从这里面挑。

  3. 维度之间相互独立，可任意组合。
     媒介 + 流派 + 光照 + 镜头 + 构图 + 调色 + 情绪 = 组合空间 ≈ 198 个词条
     任选 4 个维度的组合数是千万级。

字段说明：
  id      程序内标识
  zh      中文显示名（界面用）
  en      英文名（溯源面板用）
  inject  送进 LLM 的注入词（保持短）
  neg     可选，反向提示词（用户手动取用，不自动送 LLM）
"""

# 每个维度是否允许多选。多选的维度建议用户克制，否则又会膨胀。
STYLE_DIMENSIONS = [
    # ------------------------------------------------------------------
    {
        "key": "medium",
        "label": "媒介 / 材质",
        "hint": "用什么画出来的。单选。",
        "multi": False,
        "items": [
            {"id": "oil", "zh": "油画", "en": "oil painting",
             "inject": "oil painting, visible impasto brushwork, painterly texture"},
            {"id": "watercolor", "zh": "水彩", "en": "watercolor",
             "inject": "watercolor, soft translucent washes, paper texture"},
            {"id": "acrylic", "zh": "丙烯", "en": "acrylic",
             "inject": "acrylic paint, bold flat color, visible strokes"},
            {"id": "gouache", "zh": "水粉", "en": "gouache",
             "inject": "gouache, opaque matte color, flat even tones"},
            {"id": "pencil", "zh": "铅笔素描", "en": "pencil sketch",
             "inject": "pencil sketch, graphite linework, crosshatching"},
            {"id": "charcoal", "zh": "炭笔", "en": "charcoal drawing",
             "inject": "charcoal drawing, smudged shading, rough paper"},
            {"id": "ink_wash", "zh": "水墨", "en": "ink wash",
             "inject": "ink wash painting, flowing brush strokes, negative space"},
            {"id": "pen_ink", "zh": "钢笔画", "en": "pen and ink",
             "inject": "pen and ink, fine hatching, high contrast linework"},
            {"id": "etching", "zh": "铜版画", "en": "etching",
             "inject": "etching, fine engraved lines, plate tone"},
            {"id": "woodblock", "zh": "版画", "en": "woodblock print",
             "inject": "woodblock print, carved lines, flat color layers"},
            {"id": "ukiyoe", "zh": "浮世绘", "en": "ukiyo-e",
             "inject": "ukiyo-e woodblock, flat perspective, bold outlines"},
            {"id": "fresco", "zh": "壁画", "en": "fresco mural",
             "inject": "fresco mural, cracked plaster texture, earthy pigment"},
            {"id": "crayon", "zh": "蜡笔", "en": "crayon",
             "inject": "crayon drawing, waxy texture, visible strokes"},
            {"id": "chalk", "zh": "粉笔", "en": "chalk",
             "inject": "chalk on blackboard, dusty texture"},
            {"id": "airbrush", "zh": "喷枪", "en": "airbrush",
             "inject": "airbrush, smooth gradient shading, soft edges"},
            {"id": "cel", "zh": "赛璐璐上色", "en": "cel shading",
             "inject": "cel shading, hard-edged shadow blocks, flat color"},
            {"id": "vector", "zh": "矢量插画", "en": "vector illustration",
             "inject": "vector illustration, clean flat shapes, hard edges"},
            {"id": "pixel", "zh": "像素艺术", "en": "pixel art",
             "inject": "pixel art, limited resolution, dithering"},
            {"id": "lowpoly", "zh": "低多边形", "en": "low poly",
             "inject": "low poly, faceted flat-shaded surfaces"},
            {"id": "render3d", "zh": "3D 渲染", "en": "3D render",
             "inject": "3D render, ray-traced lighting, subsurface scattering"},
            {"id": "claymation", "zh": "粘土定格", "en": "claymation",
             "inject": "claymation, plasticine texture, stop-motion set"},
            {"id": "papercut", "zh": "剪纸", "en": "paper cutout",
             "inject": "paper cutout, layered card stock, crisp edges"},
            {"id": "origami", "zh": "折纸", "en": "origami",
             "inject": "origami, folded paper geometry, crease shadows"},
            {"id": "collage", "zh": "拼贴", "en": "collage",
             "inject": "collage, torn paper fragments, layered mixed media"},
            {"id": "mosaic", "zh": "马赛克", "en": "mosaic",
             "inject": "mosaic, small tesserae tiles, grout lines"},
            {"id": "stained_glass", "zh": "彩色玻璃", "en": "stained glass",
             "inject": "stained glass, leaded panels, backlit translucency"},
            {"id": "neon_tube", "zh": "霓虹灯管", "en": "neon tubing",
             "inject": "neon tubing, glowing glass tubes, dark backing"},
            {"id": "holographic", "zh": "全息", "en": "holographic foil",
             "inject": "holographic foil, iridescent shifting spectrum"},
            {"id": "ceramic", "zh": "陶瓷", "en": "glazed ceramic",
             "inject": "glazed ceramic, glossy crackle surface"},
            {"id": "bronze", "zh": "青铜雕塑", "en": "cast bronze",
             "inject": "cast bronze sculpture, patina, polished highlights"},
            {"id": "photography", "zh": "摄影", "en": "photograph",
             "inject": "photograph, realistic lens rendering"},
            {"id": "film_photo", "zh": "胶片摄影", "en": "film photograph",
             "inject": "35mm film photograph, natural grain, halation"},
            {"id": "large_format", "zh": "大画幅", "en": "large format photo",
             "inject": "large format photograph, extreme detail, tilt-shift"},
            {"id": "sand", "zh": "沙画", "en": "sand art",
             "inject": "sand art, granular texture, raked lines"},
            {"id": "batik", "zh": "蜡染", "en": "batik",
             "inject": "batik, wax-resist dye patterns, crackled lines"},
            {"id": "embroidery", "zh": "刺绣", "en": "embroidery",
             "inject": "embroidery, visible thread stitches, fabric weave"},
        ],
    },
    # ------------------------------------------------------------------
    {
        "key": "genre",
        "label": "流派 / 风格",
        "hint": "整体调性。单选。",
        "multi": False,
        "items": [
            # --- 科幻类 ---
            {"id": "cyberpunk", "zh": "赛博朋克", "en": "cyberpunk",
             "inject": "cyberpunk, neon signage, rain-slicked streets, holographic interfaces"},
            {"id": "steampunk", "zh": "蒸汽朋克", "en": "steampunk",
             "inject": "steampunk, brass machinery, exposed gears, gas-lamp glow"},
            {"id": "dieselpunk", "zh": "柴油朋克", "en": "dieselpunk",
             "inject": "dieselpunk, riveted steel, industrial smokestacks, chrome"},
            {"id": "biopunk", "zh": "生物朋克", "en": "biopunk",
             "inject": "biopunk, organic growth, wet tissue textures, bio-luminescence"},
            {"id": "silkpunk", "zh": "丝绸朋克", "en": "silkpunk",
             "inject": "silkpunk, bamboo mechanics, silk sails, jade circuitry"},
            {"id": "retro_scifi", "zh": "复古科幻", "en": "retro sci-fi",
             "inject": "retro sci-fi, analog dials, CRT monitors, bulbous chrome"},
            {"id": "space_opera", "zh": "太空歌剧", "en": "space opera",
             "inject": "space opera, vast starfields, colossal structures, epic scale"},
            {"id": "solarpunk", "zh": "太阳能朋克", "en": "solarpunk",
             "inject": "solarpunk, lush vegetation, glass architecture, warm optimism"},
            {"id": "wasteland", "zh": "废土", "en": "post-apocalyptic wasteland",
             "inject": "post-apocalyptic wasteland, rusted debris, dust haze, scavenged gear"},
            # --- 动画类 ---
            {"id": "ghibli", "zh": "吉卜力", "en": "Studio Ghibli",
             "inject": "Studio Ghibli, hand-painted backgrounds, warm pastoral light, nostalgic"},
            {"id": "disney2d", "zh": "迪士尼手绘", "en": "Disney hand-drawn",
             "inject": "Disney hand-drawn animation, expressive line, warm musical palette"},
            {"id": "pixar", "zh": "皮克斯 3D", "en": "Pixar 3D animation",
             "inject": "Pixar 3D animation, stylized proportions, polished CG, warm cinematic light"},
            {"id": "shinkai", "zh": "新海诚", "en": "Makoto Shinkai",
             "inject": "Makoto Shinkai, hyper-detailed skies, lens flares, saturated twilight"},
            {"id": "kon", "zh": "今敏", "en": "Satoshi Kon",
             "inject": "Satoshi Kon, unsettling realism, match cuts, psychological unease"},
            {"id": "oshi", "zh": "押井守", "en": "Mamoru Oshii",
             "inject": "Mamoru Oshii, muted palette, philosophical stillness, urban melancholy"},
            # --- 漫画类 ---
            {"id": "manga_bw", "zh": "黑白漫画", "en": "manga screentone",
             "inject": "manga, screentone shading, bold ink linework, dramatic angles"},
            {"id": "superhero", "zh": "美式超级英雄", "en": "American superhero comic",
             "inject": "American superhero comic, heavy inks, halftone dots, dynamic foreshortening"},
            {"id": "bande_dessinee", "zh": "法式漫画", "en": "bande dessinée",
             "inject": "bande dessinée, clean ligne claire, flat color, precise linework"},
            {"id": "moebius", "zh": "墨比斯", "en": "Moebius",
             "inject": "Moebius style, delicate line, vast desert emptiness, muted pastels"},
            # --- 现代艺术流派 ---
            {"id": "impressionism", "zh": "印象派", "en": "impressionism",
             "inject": "impressionism, broken brushwork, light on surfaces, plein air"},
            {"id": "post_impressionism", "zh": "后印象派", "en": "post-impressionism",
             "inject": "post-impressionism, bold structure, expressive color, thick strokes"},
            {"id": "expressionism", "zh": "表现主义", "en": "expressionism",
             "inject": "expressionism, distorted forms, jarring color, emotional intensity"},
            {"id": "fauvism", "zh": "野兽派", "en": "fauvism",
             "inject": "fauvism, wild unnatural color, flattened space, loose strokes"},
            {"id": "cubism", "zh": "立体主义", "en": "cubism",
             "inject": "cubism, fractured planes, multiple viewpoints, geometric shards"},
            {"id": "surrealism", "zh": "超现实主义", "en": "surrealism",
             "inject": "surrealism, dream logic, impossible juxtaposition, hyperreal rendering"},
            {"id": "dada", "zh": "达达主义", "en": "Dada",
             "inject": "Dada, absurd anti-art collage, irrational composition"},
            {"id": "pop_art", "zh": "波普艺术", "en": "pop art",
             "inject": "pop art, bold flat color, commercial imagery, ben-day dots"},
            {"id": "minimalism", "zh": "极简主义", "en": "minimalism",
             "inject": "minimalism, reduced forms, generous empty space, restrained palette"},
            {"id": "abstract_expr", "zh": "抽象表现主义", "en": "abstract expressionism",
             "inject": "abstract expressionism, gestural paint, allover composition, raw energy"},
            {"id": "color_field", "zh": "色域绘画", "en": "color field",
             "inject": "color field painting, large flat color areas, soft edges"},
            {"id": "op_art", "zh": "欧普艺术", "en": "op art",
             "inject": "op art, optical vibration, precise geometric patterns"},
            # --- 历史流派 ---
            {"id": "renaissance", "zh": "文艺复兴", "en": "Renaissance",
             "inject": "Renaissance painting, sfumato, balanced composition, classical anatomy"},
            {"id": "baroque", "zh": "巴洛克", "en": "Baroque",
             "inject": "Baroque, dramatic movement, rich saturated color, deep shadow"},
            {"id": "rococo", "zh": "洛可可", "en": "Rococo",
             "inject": "Rococo, pastel lightness, ornamental curves, playful elegance"},
            {"id": "romanticism", "zh": "浪漫主义", "en": "Romanticism",
             "inject": "Romanticism, sublime nature, stormy emotion, heroic scale"},
            {"id": "pre_raphaelite", "zh": "拉斐尔前派", "en": "Pre-Raphaelite",
             "inject": "Pre-Raphaelite, jewel-like detail, medieval subjects, rich color"},
            {"id": "symbolism", "zh": "象征主义", "en": "symbolism",
             "inject": "symbolism, mythic allegory, mystic atmosphere, decorative line"},
            {"id": "gothic", "zh": "哥特", "en": "Gothic",
             "inject": "Gothic, pointed arches, stained shadow, macabre grandeur"},
            # --- 设计运动 ---
            {"id": "art_deco", "zh": "装饰艺术", "en": "Art Deco",
             "inject": "Art Deco, geometric ornament, metallic accents, streamlined symmetry"},
            {"id": "art_nouveau", "zh": "新艺术运动", "en": "Art Nouveau",
             "inject": "Art Nouveau, whiplash curves, floral ornament, decorative border"},
            {"id": "bauhaus", "zh": "包豪斯", "en": "Bauhaus",
             "inject": "Bauhaus, primary colors, geometric function, sans-serif clarity"},
            {"id": "constructivism", "zh": "构成主义", "en": "constructivism",
             "inject": "constructivism, diagonal dynamism, photomontage, red and black"},
            {"id": "suprematism", "zh": "至上主义", "en": "suprematism",
             "inject": "suprematism, floating geometric shapes, pure color fields"},
            # --- 亚文化与氛围 ---
            {"id": "vaporwave", "zh": "蒸汽波", "en": "vaporwave",
             "inject": "vaporwave, pastel gradient, glitch artifacts, classical statue"},
            {"id": "synthwave", "zh": "合成器浪潮", "en": "synthwave",
             "inject": "synthwave, chrome grid horizon, magenta sunset, retro neon"},
            {"id": "dark_fantasy", "zh": "黑暗奇幻", "en": "dark fantasy",
             "inject": "dark fantasy, grim atmosphere, ornate decay, ominous scale"},
            {"id": "medieval_fantasy", "zh": "中世纪奇幻", "en": "medieval fantasy",
             "inject": "medieval fantasy, heraldic detail, candlelit stone, quest imagery"},
            {"id": "cosmic_horror", "zh": "克苏鲁", "en": "cosmic horror",
             "inject": "cosmic horror, non-euclidean geometry, vast indifference, creeping dread"},
            {"id": "j_horror", "zh": "日式恐怖", "en": "J-horror",
             "inject": "J-horror, wet darkness, long black hair, mundane spaces defiled"},
            {"id": "childrens_book", "zh": "童书插画", "en": "children's book illustration",
             "inject": "children's book illustration, gentle shapes, warm palette, hand-lettered feel"},
        ],
    },
    # ------------------------------------------------------------------
    {
        "key": "lighting",
        "label": "光照",
        "hint": "光从哪来、什么质感。单选。",
        "multi": False,
        "items": [
            {"id": "golden_hour", "zh": "黄金时刻", "en": "golden hour",
             "inject": "golden hour light, long warm shadows"},
            {"id": "blue_hour", "zh": "蓝调时刻", "en": "blue hour",
             "inject": "blue hour, deep cool ambient, early lights"},
            {"id": "sunrise", "zh": "日出", "en": "sunrise",
             "inject": "sunrise, low warm sun, morning mist"},
            {"id": "sunset", "zh": "日落", "en": "sunset",
             "inject": "sunset, orange sky gradient, silhouetted forms"},
            {"id": "noon", "zh": "正午强光", "en": "harsh noon sun",
             "inject": "harsh noon sun, short hard shadows, high contrast"},
            {"id": "overcast", "zh": "阴天漫射", "en": "overcast diffuse",
             "inject": "overcast diffuse light, soft shadowless, muted"},
            {"id": "moonlight", "zh": "月光", "en": "moonlight",
             "inject": "moonlight, pale blue cast, deep shadows"},
            {"id": "candlelight", "zh": "烛光", "en": "candlelight",
             "inject": "candlelight, warm flicker, dark surround"},
            {"id": "firelight", "zh": "篝火", "en": "firelight",
             "inject": "firelight, orange glow, dancing shadows"},
            {"id": "neon", "zh": "霓虹", "en": "neon signage",
             "inject": "neon lighting, colored tube glow, wet reflections"},
            {"id": "screen_glow", "zh": "屏幕光", "en": "screen glow",
             "inject": "screen glow, cold frontal light, face illumination"},
            {"id": "backlit", "zh": "逆光", "en": "backlit",
             "inject": "backlit, rim silhouettes, glowing edges"},
            {"id": "sidelight", "zh": "侧光", "en": "side lighting",
             "inject": "side lighting, half face in shadow"},
            {"id": "toplight", "zh": "顶光", "en": "top lighting",
             "inject": "top lighting, eye sockets shadowed"},
            {"id": "underlight", "zh": "底光", "en": "underlighting",
             "inject": "underlighting, sinister upward shadows"},
            {"id": "rembrandt", "zh": "伦勃朗光", "en": "Rembrandt lighting",
             "inject": "Rembrandt lighting, triangle cheek highlight"},
            {"id": "butterfly", "zh": "蝴蝶光", "en": "butterfly lighting",
             "inject": "butterfly lighting, centered soft shadow under nose"},
            {"id": "rim", "zh": "轮廓光", "en": "rim light",
             "inject": "rim light, bright contour separation"},
            {"id": "chiaroscuro", "zh": "明暗对照", "en": "chiaroscuro",
             "inject": "chiaroscuro, extreme light-dark contrast"},
            {"id": "volumetric", "zh": "体积光", "en": "volumetric god rays",
             "inject": "volumetric god rays, visible light shafts, dust motes"},
            {"id": "softbox", "zh": "柔光箱", "en": "softbox studio light",
             "inject": "softbox studio lighting, even soft falloff"},
            {"id": "hard_light", "zh": "硬光", "en": "hard light",
             "inject": "hard light, razor-sharp shadow edges"},
            {"id": "bioluminescence", "zh": "生物荧光", "en": "bioluminescence",
             "inject": "bioluminescent glow, organic cold light"},
            {"id": "caustics", "zh": "水下焦散", "en": "underwater caustics",
             "inject": "underwater caustics, rippling light patterns"},
            {"id": "spotlight", "zh": "舞台聚光", "en": "stage spotlight",
             "inject": "stage spotlight, hard pool of light, black surround"},
            {"id": "headlights", "zh": "车灯流动", "en": "passing headlights",
             "inject": "passing headlights, streaked motion glow"},
            {"id": "fluorescent", "zh": "荧光灯", "en": "fluorescent flicker",
             "inject": "flickering fluorescent, sickly green cast"},
            {"id": "lightning", "zh": "闪电", "en": "lightning flashes",
             "inject": "lightning flashes, hard split-second illumination"},
        ],
    },
    # ------------------------------------------------------------------
    {
        "key": "camera",
        "label": "镜头 / 视角",
        "hint": "怎么拍的。单选。",
        "multi": False,
        "items": [
            {"id": "closeup", "zh": "特写", "en": "close-up",
             "inject": "close-up shot, face fills frame"},
            {"id": "extreme_closeup", "zh": "大特写", "en": "extreme close-up",
             "inject": "extreme close-up, single detail isolated"},
            {"id": "medium_shot", "zh": "中景", "en": "medium shot",
             "inject": "medium shot, waist up framing"},
            {"id": "full_body", "zh": "全身景", "en": "full body shot",
             "inject": "full body shot, head to toe in frame"},
            {"id": "wide", "zh": "广角定场", "en": "establishing wide shot",
             "inject": "establishing wide shot, subject small in environment"},
            {"id": "ultrawide", "zh": "超广角", "en": "ultra-wide",
             "inject": "ultra-wide lens, exaggerated perspective, sweeping space"},
            {"id": "telephoto", "zh": "长焦压缩", "en": "telephoto compression",
             "inject": "telephoto compression, flattened layered depth"},
            {"id": "macro", "zh": "微距", "en": "macro",
             "inject": "macro lens, extreme magnification, shallow plane"},
            {"id": "fisheye", "zh": "鱼眼", "en": "fisheye",
             "inject": "fisheye lens, spherical distortion, curved edges"},
            {"id": "high_angle", "zh": "俯视", "en": "high angle",
             "inject": "high angle, looking down, subject diminished"},
            {"id": "low_angle", "zh": "仰视", "en": "low angle",
             "inject": "low angle, looking up, subject dominant"},
            {"id": "dutch", "zh": "荷兰角", "en": "dutch angle",
             "inject": "dutch angle, tilted horizon, unease"},
            {"id": "aerial", "zh": "鸟瞰", "en": "aerial view",
             "inject": "aerial view, straight down, pattern-like ground"},
            {"id": "drone", "zh": "无人机航拍", "en": "drone shot",
             "inject": "drone shot, elevated three-quarter perspective"},
            {"id": "ots", "zh": "过肩镜头", "en": "over-the-shoulder",
             "inject": "over-the-shoulder shot, foreground shoulder framing"},
            {"id": "pov", "zh": "主观视角", "en": "POV",
             "inject": "POV shot, first-person perspective, hands visible"},
            {"id": "shallow_dof", "zh": "浅景深", "en": "shallow depth of field",
             "inject": "shallow depth of field, creamy bokeh background"},
            {"id": "deep_focus", "zh": "深景深", "en": "deep focus",
             "inject": "deep focus, everything sharp near to far"},
            {"id": "tiltshift", "zh": "移轴", "en": "tilt-shift",
             "inject": "tilt-shift, miniature effect, selective focus band"},
            {"id": "long_exposure", "zh": "长曝光", "en": "long exposure",
             "inject": "long exposure, silky motion trails"},
            {"id": "motion_blur", "zh": "运动模糊", "en": "motion blur",
             "inject": "motion blur, streaked movement energy"},
            {"id": "two_shot", "zh": "双人镜头", "en": "two-shot",
             "inject": "two-shot, both subjects sharing frame"},
            {"id": "reflection", "zh": "反射倒影", "en": "reflection shot",
             "inject": "reflection shot, mirrored surface doubling"},
            {"id": "frame_within", "zh": "框架式", "en": "framed through foreground",
             "inject": "framed through foreground, doorway or window aperture"},
            {"id": "crane", "zh": "摇臂镜头", "en": "crane shot",
             "inject": "crane shot, elevated descending sweep"},
            {"id": "stacked", "zh": "前后景分层", "en": "layered depth",
             "inject": "layered depth, distinct foreground midground background"},
        ],
    },
    # ------------------------------------------------------------------
    {
        "key": "composition",
        "label": "构图",
        "hint": "画面怎么排。单选。",
        "multi": False,
        "items": [
            {"id": "thirds", "zh": "三分法", "en": "rule of thirds",
             "inject": "rule of thirds, subject on intersection"},
            {"id": "centered", "zh": "居中对称", "en": "centered symmetry",
             "inject": "centered symmetry, subject dead center"},
            {"id": "diagonal", "zh": "对角线", "en": "diagonal composition",
             "inject": "diagonal composition, strong corner-to-corner energy"},
            {"id": "leading_lines", "zh": "引导线", "en": "leading lines",
             "inject": "leading lines drawing eye inward"},
            {"id": "frame_in_frame", "zh": "画中画", "en": "frame within a frame",
             "inject": "frame within a frame, nested aperture"},
            {"id": "negative_space", "zh": "负空间", "en": "negative space",
             "inject": "large negative space, isolated subject"},
            {"id": "golden_spiral", "zh": "黄金螺旋", "en": "golden spiral",
             "inject": "golden spiral, spiraling visual flow"},
            {"id": "triangle", "zh": "三角形构图", "en": "triangular composition",
             "inject": "triangular composition, stable three-point structure"},
            {"id": "repeating", "zh": "重复图案", "en": "repeating patterns",
             "inject": "repeating patterns, rhythmic repetition"},
            {"id": "low_horizon", "zh": "低地平线", "en": "low horizon",
             "inject": "low horizon line, vast sky dominance"},
            {"id": "high_horizon", "zh": "高地平线", "en": "high horizon",
             "inject": "high horizon line, compressed sky, ground dominance"},
            {"id": "tight_crop", "zh": "满构图", "en": "tight crop",
             "inject": "tight crop, subject bleeding off edges"},
            {"id": "bilateral", "zh": "左右对称", "en": "bilateral symmetry",
             "inject": "bilateral symmetry, mirrored halves"},
            {"id": "radial", "zh": "放射状", "en": "radial composition",
             "inject": "radial composition, elements converging on center"},
            {"id": "empty_space", "zh": "大面积留白", "en": "large empty space",
             "inject": "large empty space, single small focal point"},
            {"id": "stacked_planes", "zh": "层叠平面", "en": "stacked planes",
             "inject": "stacked receding planes, flat depth staging"},
        ],
    },
    # ------------------------------------------------------------------
    {
        "key": "palette",
        "label": "调色",
        "hint": "颜色走向。单选。",
        "multi": False,
        "items": [
            {"id": "teal_orange", "zh": "青橙", "en": "teal and orange",
             "inject": "teal and orange grade, complementary split tone"},
            {"id": "monochrome", "zh": "单色", "en": "monochrome",
             "inject": "monochrome, single hue throughout"},
            {"id": "bw", "zh": "黑白", "en": "black and white",
             "inject": "black and white, pure tonal range"},
            {"id": "sepia", "zh": "棕褐", "en": "sepia",
             "inject": "sepia tone, aged brown cast"},
            {"id": "saturated", "zh": "高饱和高对比", "en": "saturated high contrast",
             "inject": "saturated high contrast, punchy color"},
            {"id": "desaturated", "zh": "低饱和褪色", "en": "desaturated faded",
             "inject": "desaturated faded color, washed out"},
            {"id": "pastel", "zh": "粉彩", "en": "pastel",
             "inject": "pastel palette, soft low-saturation hues"},
            {"id": "neon_clash", "zh": "霓虹撞色", "en": "neon clash",
             "inject": "clashing neon color, electric saturation"},
            {"id": "warm", "zh": "暖调", "en": "warm tones",
             "inject": "warm tones, amber and ochre bias"},
            {"id": "cool", "zh": "冷调", "en": "cool tones",
             "inject": "cool tones, blue and cyan bias"},
            {"id": "earthy", "zh": "大地色", "en": "earthy neutrals",
             "inject": "earthy neutrals, clay and moss"},
            {"id": "jewel", "zh": "宝石色调", "en": "jewel tones",
             "inject": "jewel tones, deep emerald sapphire ruby"},
            {"id": "morandi", "zh": "莫兰迪", "en": "muted Morandi",
             "inject": "muted Morandi palette, greyed dusty hues"},
            {"id": "crimson_black", "zh": "血红与黑", "en": "crimson and black",
             "inject": "crimson and black, restricted violent palette"},
            {"id": "gold_blue", "zh": "金箔与深蓝", "en": "gold leaf and deep blue",
             "inject": "gold leaf and deep blue, luminous contrast"},
            {"id": "uv_cyan", "zh": "紫外与青", "en": "ultraviolet and cyan",
             "inject": "ultraviolet and cyan, blacklight glow"},
            {"id": "autumn", "zh": "秋季暖色", "en": "autumn palette",
             "inject": "autumn palette, rust gold umber"},
            {"id": "spring", "zh": "春季粉绿", "en": "spring pastel green",
             "inject": "spring palette, fresh pink and green"},
            {"id": "winter", "zh": "冬季冷灰", "en": "winter cold grey",
             "inject": "winter palette, cold grey and pale blue"},
            {"id": "portra", "zh": "柯达暖片", "en": "warm film tones",
             "inject": "warm film stock, creamy highlights, gentle rolloff"},
            {"id": "cyber_cyan_magenta", "zh": "赛博青紫", "en": "cyan-magenta",
             "inject": "cyan and magenta duotone, synthetic glow"},
            {"id": "duotone", "zh": "双色调", "en": "duotone",
             "inject": "duotone, two-ink posterization"},
        ],
    },
    # ------------------------------------------------------------------
    {
        "key": "mood",
        "label": "情绪",
        "hint": "画面传达什么感觉。单选。",
        "multi": False,
        "items": [
            {"id": "serene", "zh": "宁静", "en": "serene",
             "inject": "serene mood, unhurried stillness"},
            {"id": "melancholic", "zh": "忧郁", "en": "melancholic",
             "inject": "melancholic mood, quiet sorrow"},
            {"id": "tense", "zh": "紧张", "en": "tense",
             "inject": "tense mood, coiled anticipation"},
            {"id": "epic", "zh": "宏大", "en": "epic",
             "inject": "epic mood, overwhelming scale"},
            {"id": "intimate", "zh": "亲密", "en": "intimate",
             "inject": "intimate mood, close quiet warmth"},
            {"id": "lonely", "zh": "孤独", "en": "lonely",
             "inject": "lonely mood, solitary isolation"},
            {"id": "joyful", "zh": "欢快", "en": "joyful",
             "inject": "joyful mood, bright open delight"},
            {"id": "mysterious", "zh": "神秘", "en": "mysterious",
             "inject": "mysterious mood, withheld information"},
            {"id": "foreboding", "zh": "不祥", "en": "foreboding",
             "inject": "foreboding mood, impending threat"},
            {"id": "nostalgic", "zh": "怀旧", "en": "nostalgic",
             "inject": "nostalgic mood, remembered warmth"},
            {"id": "dreamlike", "zh": "梦幻", "en": "dreamlike",
             "inject": "dreamlike mood, hazy unreality"},
            {"id": "oppressive", "zh": "压抑", "en": "oppressive",
             "inject": "oppressive mood, crushing enclosure"},
            {"id": "sacred", "zh": "神圣", "en": "sacred",
             "inject": "sacred mood, reverent hush"},
            {"id": "absurd", "zh": "荒诞", "en": "absurd",
             "inject": "absurd mood, deadpan incongruity"},
            {"id": "tender", "zh": "温柔", "en": "tender",
             "inject": "tender mood, gentle care"},
            {"id": "wild", "zh": "狂野", "en": "wild",
             "inject": "wild mood, untamed energy"},
            {"id": "stoic", "zh": "冷峻", "en": "stoic",
             "inject": "stoic mood, unreadable restraint"},
            {"id": "frenzied", "zh": "狂热", "en": "frenzied",
             "inject": "frenzied mood, manic overload"},
            {"id": "healing", "zh": "平静治愈", "en": "calm healing",
             "inject": "calm healing mood, safe and settled"},
            {"id": "apocalyptic", "zh": "末日感", "en": "apocalyptic",
             "inject": "apocalyptic mood, terminal finality"},
        ],
    },
]


# ---- 查询辅助 ----------------------------------------------------------

_BY_ID = {}
for _dim in STYLE_DIMENSIONS:
    for _item in _dim["items"]:
        _BY_ID[_item["id"]] = dict(_item, dimension=_dim["key"], dimension_label=_dim["label"])


def get_item(item_id):
    """按 id 取风格词条，取不到返回 None。"""
    return _BY_ID.get(item_id)


def resolve(selected):
    """把 {维度key: 词条id} 或 {维度key: [词条id,...]} 解析成词条列表。

    引擎只认这个结果——UI 传来什么 id 都在这里过一遍，
    不存在的 id 静默丢弃，避免脏数据污染 system prompt。
    """
    out = []
    if not selected:
        return out
    for dim in STYLE_DIMENSIONS:
        raw = selected.get(dim["key"])
        if not raw:
            continue
        ids = raw if isinstance(raw, list) else [raw]
        for item_id in ids:
            item = _BY_ID.get(item_id)
            # 校验这个词条确实属于它被填在的那个维度
            if item and item["dimension"] == dim["key"]:
                out.append(item)
    return out


def catalog():
    """给前端用的完整维度目录（不含 inject 之外的内部字段）。"""
    return [
        {
            "key": d["key"],
            "label": d["label"],
            "hint": d["hint"],
            "multi": d["multi"],
            "items": [
                {"id": i["id"], "zh": i["zh"], "en": i["en"]}
                for i in d["items"]
            ],
        }
        for d in STYLE_DIMENSIONS
    ]


def stats():
    return {
        "dimensions": len(STYLE_DIMENSIONS),
        "items": sum(len(d["items"]) for d in STYLE_DIMENSIONS),
    }


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    s = stats()
    print(f"维度 {s['dimensions']} 个，词条 {s['items']} 条")
    for d in STYLE_DIMENSIONS:
        print(f"  {d['label']:<12} {len(d['items']):>3} 条  多选={d['multi']}")
