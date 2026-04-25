from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from parser_ll1 import TreeNode


NODE_PADDING_X = 12
NODE_PADDING_Y = 8
HORIZONTAL_GAP = 24
VERTICAL_GAP = 70
CANVAS_MARGIN = 32


@dataclass
class LayoutNode:
    tree: TreeNode
    text: str
    width: int
    height: int
    subtree_width: int
    children: list["LayoutNode"]
    x: int = 0
    y: int = 0


def render_tree(root: TreeNode, output_path: str, include_annotations: bool = False) -> None:
    font = ImageFont.load_default()
    layout = _build_layout(root, font, include_annotations)
    _assign_positions(layout, CANVAS_MARGIN, CANVAS_MARGIN)

    max_x, max_y = _measure_bounds(layout)
    image = Image.new("RGB", (max_x + CANVAS_MARGIN, max_y + CANVAS_MARGIN), "white")
    draw = ImageDraw.Draw(image)

    _draw_edges(draw, layout)
    _draw_nodes(draw, layout, font)
    image.save(output_path, format="PNG")


def _build_layout(node: TreeNode, font: ImageFont.ImageFont, include_annotations: bool) -> LayoutNode:
    text = node.label(include_annotations)
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).multiline_textbbox((0, 0), text, font=font, spacing=2)
    width = bbox[2] - bbox[0] + (NODE_PADDING_X * 2)
    height = bbox[3] - bbox[1] + (NODE_PADDING_Y * 2)
    children = [_build_layout(child, font, include_annotations) for child in node.children]

    if not children:
        subtree_width = width
    else:
        children_width = sum(child.subtree_width for child in children) + HORIZONTAL_GAP * (len(children) - 1)
        subtree_width = max(width, children_width)

    return LayoutNode(node, text, width, height, subtree_width, children)


def _assign_positions(node: LayoutNode, left: int, top: int) -> None:
    node.y = top
    node.x = left + (node.subtree_width - node.width) // 2

    if not node.children:
        return

    child_left = left
    child_top = top + node.height + VERTICAL_GAP
    for child in node.children:
        _assign_positions(child, child_left, child_top)
        child_left += child.subtree_width + HORIZONTAL_GAP


def _measure_bounds(node: LayoutNode) -> tuple[int, int]:
    max_x = node.x + node.width
    max_y = node.y + node.height
    for child in node.children:
        child_x, child_y = _measure_bounds(child)
        max_x = max(max_x, child_x)
        max_y = max(max_y, child_y)
    return max_x, max_y


def _draw_edges(draw: ImageDraw.ImageDraw, node: LayoutNode) -> None:
    parent_center = (node.x + node.width // 2, node.y + node.height)
    for child in node.children:
        child_center = (child.x + child.width // 2, child.y)
        draw.line([parent_center, child_center], fill="#4b5563", width=2)
        _draw_edges(draw, child)


def _draw_nodes(draw: ImageDraw.ImageDraw, node: LayoutNode, font: ImageFont.ImageFont) -> None:
    fill, outline = _node_colors(node.tree)
    draw.rounded_rectangle(
        [node.x, node.y, node.x + node.width, node.y + node.height],
        radius=12,
        fill=fill,
        outline=outline,
        width=2,
    )
    draw.multiline_text(
        (node.x + NODE_PADDING_X, node.y + NODE_PADDING_Y),
        node.text,
        font=font,
        fill="black",
        spacing=2,
    )
    for child in node.children:
        _draw_nodes(draw, child, font)


def _node_colors(node: TreeNode) -> tuple[str, str]:
    status = node.annotations.get("status")
    if node.symbol == "BinaryOp":
        return "#fef3c7", "#d97706"
    if status == "error":
        return "#fee2e2", "#dc2626"
    if status == "ok":
        return "#dcfce7", "#16a34a"
    if status == "epsilon":
        return "#e5e7eb", "#6b7280"
    return "#dbeafe", "#2563eb"
