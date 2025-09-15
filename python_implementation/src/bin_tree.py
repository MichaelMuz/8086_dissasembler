from dataclasses import dataclass
from typing import Iterator


@dataclass
class Node:
    val: int
    left: "Node | None" = None
    right: "Node | None" = None


def insert_bad(head: Node, val: int) -> None:
    # This one repeats logic in both possible top levels bc both their next levels may have null head
    if val <= head.val:
        if head.left is not None:
            insert_bad(head.left, val)
        else:
            head.left = Node(val)
    else:
        if head.right is not None:
            insert_bad(head.right, val)
        else:
            head.right = Node(val)


def insert_single(head: Node | None, val: int) -> Node:
    # eliminates repetition bc bottom level for left and right case is handled in bottom level
    if head is None:
        return Node(val)

    if val <= head.val:
        head.left = insert_single(head.left, val)
    else:
        head.right = insert_single(head.right, val)

    return head


def insert(head: Node | None, val_iter: Iterator[int]) -> Node:
    # handles both inserting where something exists or inserting a sub tree by making a default head node and working with that. Always returning given head or the default one bc was given null
    val = next(val_iter)
    if head is None:
        head = Node(val)

    if val <= head.val:
        head.left = insert(head.left, val_iter)
    else:
        head.right = insert(head.right, val_iter)

    return head
