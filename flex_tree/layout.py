import copy
from typing import Optional, cast

from xcffib.xproto import StackMode
from libqtile.layout.base import Layout
from libqtile.command.base import expose_command

from .node import Node, AddMode, NotRestorableError



class FlexTree(Layout):
    """A flexible tree-based layout.

    Each tree node represents a container whose children are aligned either
    horizontally or vertically. Each window is attached to a leaf of the tree
    and takes either a calculated relative amount or a custom absolute amount
    of space in its parent container. Windows can be resized, rearranged and
    integrated into other containers.
    """
    defaults = [
        ('name', 'FlexTree', 'Layout name'),
        ('border_normal', '#333333', 'Unfocused window border color'),
        ('border_focus', '#00e891', 'Focused window border color'),
        ('border_normal_fixed', '#333333',
         'Unfocused fixed-size window border color'),
        ('border_focus_fixed', '#00e8dc',
         'Focused fixed-size window border color'),
        ('border_width', 1, 'Border width'),
        ('border_width_single', 0, 'Border width for single window'),
        ('margin', 0, 'Layout margin'),
        ('margin_single', 0, 'Layout margin for single window'),
    ]
    # If windows are added before configure() was called, the screen size is
    # still unknown, so we need to set some arbitrary initial root dimensions
    default_dimensions = (0, 0, 1000, 1000)

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(FlexTree.defaults)
        self.root = Node(None, *self.default_dimensions)
        self.focused = None
        self.add_mode = None

    @staticmethod
    def convert_names(tree):
        return [FlexTree.convert_names(n) if isinstance(n, list) else
                n.payload.name for n in tree]
    
    def definitely_find_payload(self, payload)-> Node:
        node = self.root.find_payload(payload)
        assert node is not None, f"Failed to find {payload=} from root"
        return node

    @property
    def focused_node(self) -> Optional["Node"]:
        return self.root.find_payload(self.focused)

    def info(self):
        info = super().info()
        info['tree'] = self.convert_names(self.root.tree)
        return info

    def clone(self, group):
        clone = copy.copy(self)
        clone._group = group
        clone.root = Node(None, *self.default_dimensions)
        clone.focused = None
        clone.add_mode = None
        return clone

    def add_client(self, client):
        print(f'Adding {client=}')
        node = self.root if self.focused_node is None else self.focused_node
        new = Node(client)
        try:
            self.root.restore(new)
        except NotRestorableError:
            node.add_node(new, self.add_mode)
        self.add_mode = None

    def remove(self, client):
        self.definitely_find_payload(client).remove()

    def configure(self, client, screen_rect):
        self.root.x = screen_rect.x
        self.root.y = screen_rect.y
        self.root.width = screen_rect.width
        self.root.height = screen_rect.height
        node = self.root.find_payload(client)
        
        border_width = self.border_width_single if self.root.tree == [node] \
            else self.border_width
        assert isinstance(border_width, (float, int))
        margin = self.margin_single if self.root.tree == [node] \
            else self.margin
        border_color = getattr(self, 'border_' +
                               ('focus' if client.has_focus else 'normal') +
                               ('' if node.flexible else '_fixed'))
        x, y, width, height = node.pixel_perfect
       #if node.is_inline_minimized:

       #    self.group
       #    core
        client.place(
            x,
            y,
            width-2*border_width,
            height-2*border_width,
            border_width,
            border_color,
            margin=margin,
        )
        # Always keep tiles below floating windows
        client.window.configure(stackmode=StackMode.Below)
        client.unhide()

    def focus(self, client):
        self.focused = client
        self.definitely_find_payload(client).access()

    def focus_first(self):
        return self.root.first_leaf.payload

    def focus_last(self):
        return self.root.last_leaf.payload

    def focus_next(self, win):
        next_leaf = self.definitely_find_payload(win).next_leaf
        return None if next_leaf is self.root.first_leaf else next_leaf.payload

    def focus_previous(self, win):
        prev_leaf = self.definitely_find_payload(win).prev_leaf
        return None if prev_leaf is self.root.last_leaf else prev_leaf.payload

    def focus_node(self, node):
        if node is None:
            return
        self.group.focus(node.payload)

    def refocus(self):
        self.group.focus(self.focused)

    def next(self):
        """Focus next window."""
        self.focus_node(self.focused_node.next_leaf)

    def previous(self):
        """Focus previous window."""
        self.focus_node(self.focused_node.prev_leaf)

    @expose_command()
    def recent(self):
        """Focus most recently focused window.

        (Toggles between the two latest active windows.)
        """
        nodes = [n for n in self.root.all_leafs if n is not self.focused_node]
        most_recent = max(nodes, key=lambda n: n.last_accessed)
        self.focus_node(most_recent)

    @expose_command()
    def toggle_minimize_inline(self):
        self.focused_node.toggle_minimize_inline()
        self.refocus()

    @expose_command()
    def left(self):
        """Focus window to the left."""
        self.focus_node(self.focused_node.close_left)

    @expose_command()
    def right(self):
        """Focus window to the right."""
        self.focus_node(self.focused_node.close_right)

    @expose_command()
    def up(self):
        """Focus window above."""
        self.focus_node(self.focused_node.close_up)

    @expose_command()
    def down(self):
        """Focus window below."""
        self.focus_node(self.focused_node.close_down)

    @expose_command()
    def move_left(self):
        """Move current window left."""
        self.focused_node.move_left()
        self.refocus()

    @expose_command()
    def move_right(self):
        """Move current window right."""
        self.focused_node.move_right()
        self.refocus()

    @expose_command()
    def move_up(self):
        """Move current window up."""
        self.focused_node.move_up()
        self.refocus()

    @expose_command()
    def move_down(self):
        """Move current window down."""
        self.focused_node.move_down()
        self.refocus()

    @expose_command()
    def integrate_left(self):
        """Integrate current window left."""
        self.focused_node.integrate_left()
        self.refocus()

    @expose_command()
    def integrate_right(self):
        """Integrate current window right."""
        self.focused_node.integrate_right()
        self.refocus()

    @expose_command()
    def integrate_up(self):
        """Integrate current window up."""
        self.focused_node.integrate_up()
        self.refocus()

    @expose_command()
    def integrate_down(self):
        """Integrate current window down."""
        self.focused_node.integrate_down()
        self.refocus()

    @expose_command()
    def swap(self, window1, window2):
        """Swap two windows in the tree"""
        self.definitely_find_payload(window1).swap_with(self.definitely_find_payload(window2))

    @expose_command()
    def mode_horizontal(self):
        """Next window will be added horizontally."""
        self.add_mode = AddMode.HORIZONTAL

    @expose_command()
    def mode_vertical(self):
        """Next window will be added vertically."""
        self.add_mode = AddMode.VERTICAL

    @expose_command()
    def mode_horizontal_split(self):
        """Next window will be added horizontally, splitting space of current
        window.
        """
        self.add_mode = AddMode.HORIZONTAL | AddMode.SPLIT

    @expose_command()
    def mode_vertical_split(self):
        """Next window will be added vertically, splitting space of current
        window.
        """
        self.add_mode = AddMode.VERTICAL | AddMode.SPLIT

    @expose_command()
    def size(self, x):
        """Change size of current window.

        (It's recommended to use `width()`/`height()` instead.)
        """
        self.focused_node.size = x
        self.refocus()

    @expose_command()
    def width(self, x):
        """Set width of current window."""
        self.focused_node.width = x
        self.refocus()

    @expose_command()
    def height(self, x):
        """Set height of current window."""
        self.focused_node.height = x
        self.refocus()

    @expose_command()
    def reset_size(self):
        """Reset size of current window to automatic (relative) sizing."""
        self.focused_node.reset_size()
        self.refocus()

    @expose_command()
    def grow(self, x):
        """Grow size of current window.

        (It's recommended to use `grow_width()`/`grow_height()` instead.)
        """
        self.focused_node.size += x
        self.refocus()

    @expose_command()
    def grow_width(self, x):
        """Grow width of current window."""
        self.focused_node.width += x
        self.refocus()

    @expose_command()
    def grow_height(self, x):
        """Grow height of current window."""
        self.focused_node.height += x
        self.refocus()
