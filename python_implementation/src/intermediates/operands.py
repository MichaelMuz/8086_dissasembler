from dataclasses import dataclass


@dataclass(frozen=True)
class ImmediateOperand:
    value: int
    word: bool

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class RegisterOperand:
    register_index: int
    word: bool

    REG_NAME_LOWER_AND_WORD = [
        # [lower_register_name, word_full_register_name]
        ["al", "ax"],
        ["cl", "cx"],
        ["dl", "dx"],
        ["bl", "bx"],
        ["ah", "sp"],
        ["ch", "bp"],
        ["dh", "si"],
        ["bh", "di"],
    ]

    def __str__(self) -> str:
        return self.REG_NAME_LOWER_AND_WORD[self.register_index][self.word]


@dataclass(frozen=True)
class MemoryOperand:
    memory_base: int | None
    displacement: int
    word: bool

    RM_TO_EFFECTIVE_ADDR_CALC = [
        # if there are two things in the list, the equation these bits code for are those added
        ["bx", "si"],
        ["bx", "di"],
        ["bp", "si"],
        ["bp", "di"],
        ["si"],
        ["di"],
        ["bp"],
        ["bx"],
    ]

    def __str__(self) -> str:
        equation = []
        if self.memory_base is not None:
            equation = list(self.RM_TO_EFFECTIVE_ADDR_CALC[self.memory_base])

        if self.displacement != 0:
            equation.append(str(self.displacement))
        return f"[{' + '.join(equation)}]"


type Operand = ImmediateOperand | RegisterOperand | MemoryOperand
