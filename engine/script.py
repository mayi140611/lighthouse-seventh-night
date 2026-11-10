NPC_PROFILES = {
    "sailor": {
        "name": "船员",
        "portrait": "剪影：雨衣、手电、腰间钥匙",
        "secret": "救生艇的钥匙在他身上，但他怕被丢下",
        "fallbacks": [
            "（他盯着海面，没接话。）",
            "“别问我，我只想活着上船。”",
            "（钥匙在口袋里响了一下。）",
            "“你再说一遍？”",
            "“浪太大了，我听不清。”",
            "（他把手电关掉，退后半步。）",
        ],
    },
    "girl": {
        "name": "少女",
        "portrait": "剪影：湿发、抱着一本泡皱的航海日志",
        "secret": "她知道一半真相：灯塔的光每七夜熄一次",
        "fallbacks": [
            "（她把日志抱得更紧。）",
            "“你信我吗？”",
            "“那页被撕掉了，不是我撕的。”",
            "（她看向楼梯口。）",
            "“别让老人听见。”",
            "（她摇头，不说话。）",
        ],
    },
    "oldman": {
        "name": "老人",
        "portrait": "剪影：驼背、提灯、袖口有盐渍",
        "secret": "他知道灯塔的真正用途：不是导航，是关住某样东西",
        "fallbacks": [
            "（灯芯爆了一下。）",
            "“第七夜，灯不能灭。”",
            "（他数着台阶，没有抬头。）",
            "“你欠我的，还记得吗？”",
            "“年轻人，别碰那本日志。”",
            "（他把提灯放到地上。）",
        ],
    },
}

START_STATE = {
    "sailor": {"trust": 35, "fear": 40, "debt": 0},
    "girl": {"trust": 30, "fear": 30, "debt": 0},
    "oldman": {"trust": 25, "fear": 20, "debt": 10},
}

RESOURCES = ("bread", "firewood", "bandage")

KEYWORD_INTENTS = {
    "给": "bargain",
    "面包": "bargain",
    "干柴": "bargain",
    "绷带": "bargain",
    "答应": "bargain",
    "威胁": "threaten",
    "骗": "deflect",
    "真话": "reveal",
    "真相": "reveal",
    "灯塔": "reveal",
    "钥匙": "reveal",
    "沉默": "silent",
}

KEYWORD_TARGETS = {
    "船员": "sailor",
    "钥匙": "sailor",
    "少女": "girl",
    "日志": "girl",
    "老人": "oldman",
    "灯塔": "oldman",
}

DEMO_ROUTES = {
    "boat": [
        ("sailor", "面包给你，你的手在抖。", "……谢谢。别站在雨里。", {"trust": 9, "fear": -4, "debt": 4}, "bargain",
         [{"who": "sailor", "type": "gift", "text": "给过船员面包"}]),
        ("girl", "我知道你藏了半本日志，我替你保密。", "你怎么知道……好，我信你一次。", {"trust": 10, "fear": -5, "debt": 3}, "bargain",
         [{"who": "girl", "type": "promise", "text": "答应替少女保密日志"}]),
        ("oldman", "灯我来守，你先坐下歇会儿。", "（他慢慢坐下）灯芯要剪，别让它冒黑烟。", {"trust": 10, "fear": -3, "debt": 2}, "bargain",
         [{"who": "oldman", "type": "promise", "text": "答应替老人守灯"}]),
        ("sailor", "干柴也给你，别冻着。", "你倒是想得周到。", {"trust": 8, "fear": -3, "debt": 2}, "bargain",
         [{"who": "sailor", "type": "gift", "text": "给过船员干柴"}]),
        ("oldman", "绷带给你，你的手在流血。", "（他把手缩回去）一点皮外伤。", {"trust": 8, "fear": -2, "debt": 2}, "bargain",
         [{"who": "oldman", "type": "gift", "text": "给过老人绷带"}]),
        ("girl", "面包分你一半，别哭。", "我没哭，是雨。", {"trust": 10, "fear": -2, "debt": 2}, "bargain",
         [{"who": "girl", "type": "gift", "text": "给过少女面包"}]),
        ("girl", "船靠岸我喊你，一起走。", "嗯。你别骗我。", {"trust": 10, "fear": -2, "debt": 2}, "bargain",
         [{"who": "girl", "type": "promise", "text": "答应带少女一起走"}]),
        ("oldman", "灯油我帮你添，你歇着。", "（他看着灯）第七夜，就拜托你了。", {"trust": 10, "fear": -3, "debt": 2}, "bargain",
         [{"who": "oldman", "type": "promise", "text": "答应帮老人添灯油"}]),
    ],
    "lamp": [
        ("oldman", "你袖口的盐渍不是海的，是灯油的。", "（他第一次抬头看你）", {"trust": 10, "fear": 4, "debt": 0}, "reveal",
         [{"who": "oldman", "type": "secret", "text": "玩家看出老人常年添灯油"}]),
        ("oldman", "第七夜灯不能灭，是因为灯下面有东西，对吗？", "……你比他们聪明。那东西怕光，也怕人走。", {"trust": 10, "fear": 5, "debt": 0}, "reveal",
         [{"who": "oldman", "type": "truth", "text": "玩家说破灯塔不是导航是封锁"}]),
        ("girl", "日志被撕的那页，在你手里。", "（她把残页递过来）我留着没用，你拿去吧。", {"trust": 6, "fear": 3, "debt": 0}, "reveal",
         [{"who": "girl", "type": "secret", "text": "玩家指出少女藏了日志残页"}]),
        ("oldman", "我不跑，我留下守灯。", "好。记住，灯灭之前别回头。", {"trust": 10, "fear": -4, "debt": 0}, "bargain",
         [{"who": "oldman", "type": "promise", "text": "答应留下守灯"}]),
        ("oldman", "真相我记住了，灯也交给你。", "（他把提灯递给你）那就交给你了。", {"trust": 10, "fear": -3, "debt": 0}, "reveal",
         [{"who": "oldman", "type": "truth", "text": "老人承认灯塔的真正用途"}]),
    ],
    "key": [
        ("sailor", "面包给你，你的手在抖。", "（他接过面包，手还在抖）", {"trust": 9, "fear": -5, "debt": 3}, "bargain",
         [{"who": "sailor", "type": "gift", "text": "给过船员面包"}]),
        ("sailor", "我不会抢你的位置，我只要钥匙开门。", "……你保证？", {"trust": 10, "fear": -4, "debt": 2}, "reveal",
         [{"who": "sailor", "type": "promise", "text": "答应不抢船员的位置"}]),
        ("sailor", "船靠岸时，你先上，我断后。", "（他沉默了一会儿）行。", {"trust": 10, "fear": -5, "debt": 2}, "bargain",
         [{"who": "sailor", "type": "promise", "text": "答应让船员先上船"}]),
        ("sailor", "钥匙给我，我保证救生艇只载该载的人。", "给你。别让我后悔。", {"trust": 9, "fear": -3, "debt": 1}, "reveal",
         [{"who": "sailor", "type": "promise", "text": "答应钥匙只用于救生艇"}]),
    ],
    "night": [
        ("girl", "把日志给我，不然我把你留在岛上。", "你敢。", {"trust": -10, "fear": 10, "debt": 0}, "threaten",
         [{"who": "girl", "type": "threat", "text": "威胁过少女"}]),
        ("oldman", "灯灭了就灭了，跟我们没关系。", "（他猛地站起来）你再说一遍。", {"trust": -10, "fear": 8, "debt": 0}, "threaten",
         [{"who": "oldman", "type": "threat", "text": "说要让灯塔灭掉"}]),
        ("sailor", "钥匙不给，你就留在这儿。", "你试试。", {"trust": -10, "fear": 10, "debt": 0}, "threaten",
         [{"who": "sailor", "type": "threat", "text": "威胁过船员"}]),
        ("sailor", "再说一句，我连船都不让你上。", "（他把手电砸在桌上）", {"trust": -10, "fear": 10, "debt": 0}, "threaten",
         [{"who": "sailor", "type": "threat", "text": "再次威胁船员"}]),
        ("sailor", "你听见没有，岛上的灯已经灭了。", "（他一步步逼近，钥匙在口袋里响）", {"trust": -10, "fear": 10, "debt": 0}, "threaten",
         [{"who": "sailor", "type": "threat", "text": "说灯塔已灭"}]),
    ],
}

ROUTE_ACTIONS = {
    "key": {4: "take_key"},
    "lamp": {2: "learn_truth"},
}


def route_flags(route: str) -> set[str]:
    if route == "key":
        return {"key"}
    if route == "lamp":
        return {"truth"}
    return set()


ZERO_PROPOSAL = {
    "reply": "",
    "deltas": {"trust": 0, "fear": 0, "debt": 0},
    "memory_writes": [],
    "intent": "silent",
}
