from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from parser_ll1 import TreeNode


SCALE = 4
NODE_PADDING_X = 20 * SCALE
NODE_PADDING_Y = 20 * SCALE
HORIZONTAL_GAP = 30 * SCALE
VERTICAL_GAP = 60 * SCALE
CANVAS_MARGIN = 40 * SCALE
NODE_SIZE = 90 * SCALE


@dataclass
class LayoutNode:
    tree: TreeNode
    text: str
    width: int
    height: int
    subtree_width: int
    children: list["LayoutNode"]
    depth: int = 0
    x: int = 0
    y: int = 0


def render_error(message: str, output_path: str) -> None:
    try:
        font = ImageFont.truetype("arialbd.ttf", 28 * SCALE)
    except IOError:
        try:
            font = ImageFont.truetype("arial.ttf", 28 * SCALE)
        except IOError:
            font = ImageFont.load_default()

    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = dummy.textbbox((0, 0), message, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = CANVAS_MARGIN * 2
    img_w = max(text_w + padding * 2, NODE_SIZE * 3)
    img_h = max(text_h + padding * 2, NODE_SIZE * 2)

    image = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(image)

    node_w = text_w + NODE_PADDING_X * 2
    node_h = text_h + NODE_PADDING_Y * 2
    node_x = (img_w - node_w) // 2
    node_y = (img_h - node_h) // 2

    draw.ellipse([node_x, node_y, node_x + node_w, node_y + node_h],
                 fill="#fee2e2", outline="#dc2626", width=3 * SCALE)

    tx = node_x + (node_w - text_w) // 2 - bbox[0]
    ty = node_y + (node_h - text_h) // 2 - bbox[1]
    draw.text((tx, ty), message, font=font, fill="#7f1d1d")

    orig_w, orig_h = image.size
    image = image.resize((orig_w // SCALE, orig_h // SCALE), Image.Resampling.LANCZOS)
    image.save(output_path, format="PNG")


def render_tree(root: TreeNode, output_path: str, include_annotations: bool = False) -> None:
    try:
        font = ImageFont.truetype("arialbd.ttf", 28 * SCALE)
    except IOError:
        try:
            font = ImageFont.truetype("arial.ttf", 28 * SCALE)
        except IOError:
            font = ImageFont.load_default()
    layout = _build_layout(root, font, include_annotations, 0)
    _assign_positions(layout, CANVAS_MARGIN, CANVAS_MARGIN)

    max_x, max_y = _measure_bounds(layout)
    image = Image.new("RGB", (max_x + CANVAS_MARGIN, max_y + CANVAS_MARGIN), "white")
    draw = ImageDraw.Draw(image)

    _draw_edges(draw, layout)
    _draw_nodes(draw, layout, font)
    
    orig_w, orig_h = image.size
    image = image.resize((orig_w // SCALE, orig_h // SCALE), Image.Resampling.LANCZOS)
    image.save(output_path, format="PNG")


def _build_layout(node: TreeNode, font: ImageFont.ImageFont, include_annotations: bool, depth: int) -> LayoutNode:
    text = node.label(include_annotations)
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).multiline_textbbox((0, 0), text, font=font, spacing=2 * SCALE)
    
    width = NODE_SIZE
    height = NODE_SIZE
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    if text_w + (NODE_PADDING_X * 2) > width:
        width = text_w + (NODE_PADDING_X * 2)
        height = width
    if text_h + (NODE_PADDING_Y * 2) > height:
        height = text_h + (NODE_PADDING_Y * 2)
        width = height
        
    children = [_build_layout(child, font, include_annotations, depth + 1) for child in node.children]

    if not children:
        subtree_width = width
    else:
        children_width = sum(child.subtree_width for child in children) + HORIZONTAL_GAP * (len(children) - 1)
        subtree_width = max(width, children_width)

    return LayoutNode(node, text, width, height, subtree_width, children, depth)


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
    parent_center = (node.x + node.width // 2, node.y + node.height // 2)
    for child in node.children:
        child_center = (child.x + child.width // 2, child.y + child.height // 2)
        draw.line([parent_center, child_center], fill="#3D1053", width=3 * SCALE)
        _draw_edges(draw, child)


def _draw_nodes(draw: ImageDraw.ImageDraw, node: LayoutNode, font: ImageFont.ImageFont) -> None:
    fill, outline, text_color = _node_colors(node.tree, node.depth)
    draw.ellipse(
        [node.x, node.y, node.x + node.width, node.y + node.height],
        fill=fill,
        outline=outline,
        width=3 * SCALE,
    )
    
    # Center text inside the circle perfectly
    bbox = draw.textbbox((0, 0), node.text, font=font, spacing=2 * SCALE)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = node.x + (node.width - text_w) / 2 - bbox[0]
    text_y = node.y + (node.height - text_h) / 2 - bbox[1]
    
    draw.multiline_text(
        (text_x, text_y),
        node.text,
        font=font,
        fill=text_color,
        spacing=2 * SCALE,
        align="center"
    )
    for child in node.children:
        _draw_nodes(draw, child, font)


def _node_colors(node: TreeNode, depth: int) -> tuple[str, str, str]:
    # Returns (fill, outline, text_color)
    status = node.annotations.get("status")
    if status == "error":
        return "#fee2e2", "#dc2626", "#7f1d1d"
    if status == "epsilon":
        return "#f3f4f6", "#9ca3af", "#374151"
        
    # Palettes for different depths
    palettes = [
        ("#F4E8FC", "#3D1053", "#3D1053"), # 0: Purple
        ("#E8F0FE", "#102A53", "#102A53"), # 1: Blue
        ("#E8FCE8", "#105320", "#105320"), # 2: Green
        ("#FCF4E8", "#533310", "#533310"), # 3: Orange
        ("#FCE8E8", "#531010", "#531010"), # 4: Red
    ]
    return palettes[depth % len(palettes)]
