from .models import MemoryEntry


def _tokens(text: str) -> set[str]:
    text = (text or "").lower()
    for ch in "，。！？、；：（）“”‘’ \t\n":
        text = text.replace(ch, " ")
    return {tok for tok in text.split(" ") if tok}


class MemoryStore:
    def __init__(self) -> None:
        self.entries: list[MemoryEntry] = []

    def add(self, who: str, type_: str, text: str, turn: int) -> MemoryEntry:
        entry = MemoryEntry(who=who, type=type_, text=text, turn=turn)
        self.entries.append(entry)
        return entry

    def add_many(self, writes, turn: int) -> list[MemoryEntry]:
        added = []
        for item in writes or []:
            added.append(
                self.add(
                    who=item["who"],
                    type_=item["type"],
                    text=item["text"],
                    turn=item.get("turn", turn),
                )
            )
        return added

    def retrieve(self, who: str, query: str, turn: int, k: int = 6) -> list[MemoryEntry]:
        query_tokens = _tokens(query)

        def score(entry: MemoryEntry) -> tuple[int, int]:
            overlap = len(query_tokens & _tokens(entry.text))
            weight = overlap * 2 if entry.who == who else overlap
            return (weight, entry.turn)

        candidates = [e for e in self.entries if e.who == who or score(e)[0] > 0]
        ranked = sorted(candidates, key=score, reverse=True)
        return ranked[:k]

    def render(self, entries: list[MemoryEntry]) -> list[str]:
        return [f"[第{e.turn}轮|{e.type}] {e.text}" for e in entries]

    def all_for(self, who: str) -> list[MemoryEntry]:
        return [e for e in self.entries if e.who == who]
