# --------------------------------------------------------------------------------
#   Munqy, a 2D engine using Python, pymunk and PyQt5
#   (c) Pierre Denis 2021-2025
# --------------------------------------------------------------------------------

import sys
from math import degrees, hypot
from itertools import islice
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pymunk
import pymunk.autogeometry
# try:
#     from winsound import Beep, PlaySound, SND_ASYNC, SND_FILENAME
#     import threading
#     import queue
# except ImportError:
#     Beep = None
from sound import Sound

SIMULATION_TIME_STEP = 5e-3  # in sec
TIMER_ELAPSE = 10e-3  # in sec
DELTA_ELAPSE = 1e-3  # in sec
WIREFRAME_MODE = False
WIREFRAME_OPAQUE = False
TRACE_LENGTH = 10
MOUSE_BUTTON = 0x40000000
HIDE_CURSOR = False


class Item(pymunk.Body):
    """ Item is an abstract class inheriting pymunk's Body class.
        Each subclass should define a specific Shaqe instance, which encompasses
        - the item's shapes (used in particular by pymunk for collision handling)
        - the item's graphical representation, as a PyQt QGraphicsItem
        Each instance of Item's subclass can then be added in a pymunk space
        (for physical simulation) and in a PyQt Graphics Scene (for representation
        in a display). See MQSpace class, inheriting pymunk's Space and PyQt's
        QGraphicsScene.
        After each pymunk simulation step, QGraphicsItem's position and rotation are
        updated according to the shape's.
    """

    __slots__ = ('shaqe', 'qg_item', 'child_shapes', 'is_alive', 'fading_time', 'end_time', 'collision_function')

    transient_items = []

    def do_initialize(self):
        pass

    def do_finalize(self):
        pass

    def do_fading(self):
        if self.end_time is not None:
            self.qg_item.setOpacity((max(0.0, self.end_time - space.time)) / (self.end_time - self.fading_time))

    def __init__(self, position, angle, shaqe, **kwargs):
        mass = kwargs.pop("mass", 0.0)
        moment = kwargs.pop("moment", float('inf'))
        body_type = kwargs.pop("body_type", DYNAMIC)
        velocity = kwargs.pop("velocity", None)
        angular_velocity = kwargs.pop("angular_velocity", None)
        if body_type is STATIC:
            assert velocity is None and angular_velocity is None
        pymunk.Body.__init__(self, mass, moment, body_type)
        # self.is_airy = kwargs.pop("is_airy", False)
        if body_type is STATIC:
            # TODO
            self.body = space.static_body
        else:
            self.position_func = self.__class__._position_func
            if velocity is not None:
                self.velocity = velocity
            if angular_velocity is not None:
                self.angular_velocity = angular_velocity
            self.body = self
        self.body.position = position
        self.body.angle = angle
        self.shaqe = shaqe
        # the following two assignments are meant to avoid double indirections (optimisation)
        self.child_shapes = shaqe.shapes
        self.qg_item = shaqe.qg_item
        self.set_body(self.body)
        if position is not None:
            self.qg_item.setPos(*position)
            self.qg_item.setRotation(degrees(angle))
        if space.attractive_item is not None:
            self.velocity_func = Item._central_gravity_velocity_func
        self.is_alive = False
        self.fading_time = None
        self.end_time = None
        duration_s = kwargs.get("duration_s")
        if duration_s is not None:
            with_fading = kwargs.get("with_fading", False)
            self.set_transient(duration_s, with_fading)
        self.do_initialize()
        if body_type == KINEMATIC:
            space.kinematic_items.append(self)
        self.collision_function = None

    def set_body(self, body):
        for child_shape in self.child_shapes:
            child_shape.body = body
            child_shape.collision_type = id(body.__class__)

    def _position_func(self, dt):
        Item.update_position(self, dt)
        self.qg_item.setPos(*self.position)
        self.qg_item.setRotation(degrees(self.angle))

    def _central_gravity_velocity_func(self, gravity, damping, dt):
        (x, y) = self.position
        (cx, cy) = space.attractive_item.position
        dx = cx - x
        dy = cy - y
        d3 = hypot(dx, dy) ** 3
        if d3 > 0.0:
            # Newton's law of gravitation
            f = space.attractive_item_force / hypot(dx, dy) ** 3
            # shell theorem: if the body is inside the sphere (c < 1), then only the inner sphere's mass shall be considered
            c = d3 / space.attractive_item_radius ** 3
            if c < 1:
                f *= c
            pymunk.Body.update_velocity(self, (f * dx, f * dy), damping, dt)

    @staticmethod
    def remove_transient_items():
        if len(Item.transient_items) == 0:
            return
        t = space.time
        first_kept_idx = len(Item.transient_items) + 1
        for (idx, (t1, items)) in enumerate(Item.transient_items):
            if t < t1:
                first_kept_idx = idx
                break
        if first_kept_idx > 0:
            for (_, items) in islice(Item.transient_items, first_kept_idx):
                for item in items:
                    space.remove_item(item)
            del Item.transient_items[:first_kept_idx]
        for (_, items) in Item.transient_items:
            for item in items:
                if item.with_fading:
                    item.do_fading()

    def set_transient(self, duration_s, with_fading=False):
        Item.set_all_transient((self,), duration_s, with_fading)

    @staticmethod
    def set_all_transient(items, duration_s, with_fading=False):
        fading_time = space.time
        end_time = fading_time + duration_s
        for item in items:
            item.fading_time = fading_time
            item.with_fading = with_fading
            item.end_time = end_time
        insert_idx = len(Item.transient_items)
        for (idx, (t, _)) in enumerate(Item.transient_items):
            if end_time <= t:
                insert_idx = idx
                break
        Item.transient_items.insert(insert_idx, (end_time, items))

    def declare_kinematic(self):
        space.items_to_set_kinematic.add(self)

    def do_update_velocity(self):
        pass


class Shaqe:
    """ Shake is an abstract class. Each subclass allows defining some Item subclass through
        - the item's shapes (used in particular by pymunk for collision handling),
        - the item's graphical representation, as a PyQt QGraphicsItem
    """

    __slots__ = ("qg_item", "shapes")

    NO_PEN = QPen(Qt.NoPen)
    NO_BRUSH = QBrush(Qt.NoBrush)
    WIREFRAME_PEN = QPen(Qt.white)
    WIREFRAME_PEN.setWidth(0)

    def __init__(self, qg_item, *shapes, **kwargs):
        self.qg_item = qg_item
        pen = kwargs.pop("pen", None)
        brush = kwargs.pop("brush", None)
        self.set_pen(pen)
        self.set_brush(brush)
        self.shapes = tuple(shapes)
        density = kwargs.pop("density", None)
        elasticity = kwargs.pop("elasticity", None)
        friction = kwargs.pop("friction", None)
        collision_type = kwargs.pop("collision_type", None)
        for shape in shapes:
            if density is not None:
                shape.density = density
            if elasticity is not None:
                shape.elasticity = elasticity
            if friction is not None:
                shape.friction = friction
            if collision_type is not None:
                shape.collision_type = collision_type

    def set_pen(self, pen):
        if WIREFRAME_MODE:
            pen = Shaqe.WIREFRAME_PEN
        elif pen is None:
            pen = Shaqe.NO_PEN
        self.qg_item.setPen(pen)

    def set_brush(self, brush):
        if WIREFRAME_MODE:
            brush = Qt.black if WIREFRAME_OPAQUE else Shaqe.NO_BRUSH
        elif brush is None:
            brush = Shaqe.NO_BRUSH
        self.qg_item.setBrush(brush)


class CircleShaqe(Shaqe):
    """ CircleShaqe is a Shaqe subclass for defining a disk item with a given radius
    """

    def __init__(self, radius, offset=(0.0, 0.0), is_airy=False, **kwargs):
        shapes = (pymunk.Circle(None, radius, offset),) if not is_airy else ()
        (rx, ry) = offset
        Shaqe.__init__(self,
                       QGraphicsEllipseItem(rx - radius, ry - radius, 2 * radius, 2 * radius),
                       *shapes,
                       **kwargs)


class CircleItem(Item):
    """ CircleItem is an Item subclass for defining a disk item with a given radius
    """

    def __init__(self, position, angle, radius, **kwargs):
        Item.__init__(self, position, angle,
                      CircleShaqe(radius, **kwargs), **kwargs)


class RectShaqe(Shaqe):
    """ RectShaqe is a Shaqe subclass for defining a rectangle item with a given size
    """

    def __init__(self, size, offset=(0.0, 0.0), is_airy=False, **kwargs):
        (w, h) = size
        w2 = w / 2.0
        h2 = h / 2.0
        (rx, ry) = offset
        vertices = ((rx - w2, ry - h2), (rx - w2, ry + h2), (rx + w2, ry + h2), (rx + w2, ry - h2))
        # shapes = (pymunk.Poly.create_box(None,size=size),) if not is_airy else ()
        shapes = (pymunk.Poly(None, vertices),) if not is_airy else ()
        pen = kwargs.get("pen")
        d = 0.0 if pen is None or pen.style() == Qt.NoPen or WIREFRAME_MODE else pen.widthF()
        Shaqe.__init__(self, QGraphicsRectItem(rx - w2 + d / 2.0, ry - h2 + d / 2.0, w - d, h - d),
                       *shapes, **kwargs)


class RectItem(Item):
    """ RectItem is an Item subclass for defining a rectangle item with a given size
    """

    def __init__(self, position, angle, size, **kwargs):
        Item.__init__(self, position, angle,
                      RectShaqe(size, **kwargs), **kwargs)


class TextShaqe(Shaqe):
    """ TextShaqe is a Shaqe subclass for defining a text item with a given font
    """

    def __init__(self, text, font_size=None, font_family=None, offset=(0.0, 0.0), is_airy=False, **kwargs):
        qg_text_item = QGraphicsSimpleTextItem(text)
        if font_size is not None:
            font = qg_text_item.font()
            font.setPixelSize(font_size)
            qg_text_item.setFont(font)
        if font_family is not None:
            font = qg_text_item.font()
            font.setFamily(font_family)
            qg_text_item.setFont(font)
        br = qg_text_item.sceneBoundingRect()
        (self.width, self.height) = (br.width(), br.height())
        w2 = self.width / 2.0
        h2 = self.height / 2.0
        (rx, ry) = offset
        qg_text_item.setPos(rx - w2, ry - h2)
        # qg_text_item.setTransform(QTransform().translate(rx-w2,ry-h2))
        vertices = ((rx - w2, ry - h2), (rx - w2, ry + h2), (rx + w2, ry + h2), (rx + w2, ry - h2))
        shapes = (pymunk.Poly(None, vertices),) if not is_airy else ()
        Shaqe.__init__(self, qg_text_item, *shapes, **kwargs)


class TextItem(Item):
    """ TextItem is an Item subclass for defining a text item with a given font
    """

    __slots__ = ("center_pos",)

    def __init__(self, position, angle, text, font_size=None, font_family=None, **kwargs):
        text_shaqe = TextShaqe(text, font_size, font_family, **kwargs)
        Item.__init__(self, position, angle, text_shaqe, **kwargs)
        self.center_pos = (text_shaqe.width / 2.0, text_shaqe.height / 2.0)

    def _position_func(self, dt):
        Item.update_position(self, dt)
        (x, y) = self.position
        (cx, cy) = self.center_pos
        self.qg_item.setTransform(QTransform().translate(cx, cy).rotate(degrees(self.angle)).translate(-cx, -cy))
        self.qg_item.setPos(x - cx, y - cy)


class PolygonShaqe(Shaqe):
    """ PolygonShaqe is a Shaqe subclass for defining a polygon item with given vertices
    """

    def __init__(self, vertices, is_airy=False, **kwargs):
        vertices = list(vertices)
        if vertices[0] != vertices[-1]:
            vertices.append(vertices[0])
        vertices = tuple(vertices)
        convex_polygons = pymunk.autogeometry.convex_decomposition(vertices, tolerance=0.1)
        if is_airy:
            shapes = ()
        else:
            shapes = tuple(pymunk.Poly(None, vertices=vertices2) for vertices2 in convex_polygons)
        qg_polygon_item = QGraphicsPolygonItem(QPolygonF(tuple(QPointF(x, y) for (x, y) in vertices)))
        Shaqe.__init__(self, qg_polygon_item, *shapes, **kwargs)

    @staticmethod
    def build_from_matrix(matrix, char, block_size, soft=False, **kwargs):
        def sample_func(point):
            (x, y) = point
            return 1 if matrix[int(y)][int(x)] == char else 0

        w = len(matrix[0]) + 2
        h = len(matrix) + 2
        char2 = chr(ord(char) + 1)
        matrix = (w * char2,) + tuple(char2 + line + char2 for line in matrix) + (w * char2,)
        polygon_shaqes = []
        march_func = pymunk.autogeometry.march_soft if soft else pymunk.autogeometry.march_hard
        for s in march_func(pymunk.BB(0, 0, w - 1, h - 1), w, h, 0.5, sample_func):
            vertices = ((block_size * v.x, block_size * v.y) for v in s)
            polygon_shaqes.append(PolygonShaqe(vertices, **kwargs))
        return polygon_shaqes

    # TODO required for QGraphicsGroup NOK should be put on CompoundShaqe
    # def set_pen(self, pen):
    #     if WIREFRAME_MODE:
    #         pen = Shaqe.WIREFRAME_PEN
    #     elif pen is None:
    #         pen = Shaqe.NO_PEN
    #     for child_qg_item in self.qg_item.childItems():
    #         child_qg_item.setPen(pen)
    #
    # def set_brush(self,brush):
    #     if WIREFRAME_MODE:
    #         brush = Qt.black if WIREFRAME_OPAQUE else Shaqe.NO_BRUSH
    #     elif brush is None:
    #         brush = Shaqe.NO_BRUSH
    #     for child_qg_item in self.qg_item.childItems():
    #         child_qg_item.setBrush(brush)
    #


class PolygonItem(Item):
    """ PolygonItem is an Item subclass for defining a polygon item with given vertices
    """

    def __init__(self, position, angle, vertices, **kwargs):
        Item.__init__(self, position, angle,
                      PolygonShaqe(vertices, **kwargs), **kwargs)


class QGraphicsArcItem(QGraphicsEllipseItem):
    """ QGraphicsArcItem is a QGraphicsEllipseItem subclass for drawing an arc
    """

    def paint(self, painter, option, widget):
        painter.setPen(self.pen())
        # painter->setBrush(brush());
        painter.drawArc(self.rect(), self.startAngle(), self.spanAngle())


class SegmentShaqe(Shaqe):
    """ SegmentShaqe is a Shaqe subclass for defining an arc item with given size
    """

    pen_dict = {}

    def __init__(self, size, color_name, offset=(0., 0.), is_airy=False, **kwargs):
        (width, height) = size
        w2 = width / 2.0
        h2 = height / 2.0
        pen = SegmentShaqe.pen_dict.get((color_name, height))
        if pen is None:
            pen = SegmentItem.pen_dict[(color_name, height)] = QPen(QColor(color_name), height, cap=Qt.RoundCap)
        (cx, cy) = offset
        shapes = (pymunk.Segment(None, a=(cx - w2, cy), b=(cx + w2, cy), radius=h2),) if not is_airy else ()
        if WIREFRAME_MODE:
            qg_item = QGraphicsItemGroup()
            if WIREFRAME_OPAQUE:
                f = QGraphicsLineItem(cx - w2, cy, cx + w2, cy)
                f.setPen(QPen(Qt.black, height, cap=Qt.RoundCap))
                qg_item.addToGroup(f)
            qg_item.addToGroup(QGraphicsLineItem(cx - w2, cy - h2, cx + w2, cy - h2))
            qg_item.addToGroup(QGraphicsLineItem(cx - w2, cy + h2, cx + w2, cy + h2))
            # left_arc = QGraphicsEllipseItem(cx-w2-h2,cy-h2,height,height)
            left_arc = QGraphicsArcItem(cx - w2 - h2, cy - h2, height, height)
            left_arc.setStartAngle(+90.0 * 16)
            left_arc.setSpanAngle(180.0 * 16)
            qg_item.addToGroup(left_arc)
            right_arc = QGraphicsArcItem(cx + w2 - h2, cy - h2, height, height)
            right_arc.setStartAngle(-90.0 * 16)
            right_arc.setSpanAngle(180.0 * 16)
            qg_item.addToGroup(right_arc)
        else:
            qg_item = QGraphicsLineItem(cx - w2, cy, cx + w2, cy)
        Shaqe.__init__(self, qg_item, *shapes, pen=pen, **kwargs)

    def set_pen(self, pen):
        if WIREFRAME_MODE:
            for child_qg_item in self.qg_item.childItems():
                if child_qg_item.pen().capStyle() != Qt.RoundCap:
                    child_qg_item.setPen(Shaqe.WIREFRAME_PEN)
        else:
            self.qg_item.setPen(pen)

    def set_brush(self, ignored_brush):
        pass


class SegmentItem(Item):
    """ SegmentItem is an Item subclass for defining an arc item with given size
    """

    pen_dict = {}

    def __init__(self, position, angle, size, color, **kwargs):
        Item.__init__(self, position, angle,
                      SegmentShaqe(size, color, **kwargs), **kwargs)


class PixmapShaqe(Shaqe):
    """ PixmapShaqe is a Shaqe subclass for defining a rectangle item rendered with a given pixmap
    """

    def __init__(self, pixmap_filename, rounded, is_airy=False, **kwargs):
        pixmap = QPixmap.fromImageReader(QImageReader(pixmap_filename))
        size = (width, height) = (pixmap.width(), pixmap.height())
        qg_item = QGraphicsPixmapItem(pixmap)
        qg_item.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        w2 = width / 2.0
        h2 = height / 2.0
        qg_item.setOffset(-w2, -h2)
        if is_airy:
            shapes = ()
        elif rounded:
            shapes = (pymunk.Segment(None, a=(-w2 + h2, 0.), b=(+w2 - h2, 0.), radius=h2),)
        else:
            shapes = (pymunk.Poly.create_box(None, size=size),)
        Shaqe.__init__(self, qg_item, *shapes, **kwargs)

    def set_pen(self, pen):
        pass

    def set_brush(self, brush):
        pass


class PixmapItem(Item):
    """ PixmapItem is an Item subclass for defining a rectangle item rendered with a given pixmap
    """

    def __init__(self, position, angle, pixmap_filename, rounded, **kwargs):
        Item.__init__(self, position, angle,
                      PixmapShaqe(pixmap_filename, rounded, **kwargs), **kwargs)


class CompoundShaqe(Shaqe):
    """ CompoundShaqe is a Shaqe subclass for defining a compound item with given child Shaqe instances
    """

    def __init__(self, *child_shaqes, is_airy=False, **kwargs):
        # self.child_shaqes = child_shaqes
        qg_item_group = QGraphicsItemGroup()
        for child_shaqe in child_shaqes:
            qg_item_group.addToGroup(child_shaqe.qg_item)
        if is_airy:
            shapes = iter(())
        else:
            shapes = (shape for child_shaqe in child_shaqes
                      for shape in child_shaqe.shapes)
            # if not child_shaqe.is_airy
        """
        if "pen" in kwargs:
            del kwargs["pen"]
        if "brush" in kwargs:
            del kwargs["brush"]
        """
        Shaqe.__init__(self, qg_item_group, *shapes, **kwargs)

    def set_pen(self, pen):
        pass

    def set_brush(self, brush):
        pass


class CompoundItem(Item):
    """ CompoundItem is an Item subclass for defining a compound item with given child Shaqe instances
    """

    def __init__(self, position, angle, *child_shaqes, **kwargs):
        Item.__init__(self, position, angle,
                      CompoundShaqe(*child_shaqes, **kwargs), **kwargs)

    @staticmethod
    def build_from_matrix(position, angle, matrix, char, block_size, soft=False, **kwargs):
        child_shaqes = PolygonShaqe.build_from_matrix(matrix, char, block_size, soft=False, **kwargs)
        return CompoundItem(position, angle, *child_shaqes, **kwargs)


class CompoundItemDecomposable(CompoundItem):
    """ CompoundItemDecomposable is a CompoundItem subclass for defining a compound item with given child Shaqe instances,
        which can be decomposed into its Item child instances
    """

    __slots__ = ('child_items',)

    def __init__(self, position, angle, *items, **kwargs):
        child_shaqes = (item.shaqe for item in items)
        CompoundItem.__init__(self, position, angle, *child_shaqes, **kwargs)
        self.child_items = tuple(items)


class MQSpace(pymunk.Space, QGraphicsScene):
    """ MQSpace is a class inheriting from pymunk's Space class and PyQt's QGraphicsScene class;
        an instance of MQSpace can be populated by Item instances, which are handled by pymunk's Space methods
        (for physical simulation) and by PyQt Graphics Scene (for representation in a PyQt Graphics View);
        after each pymunk simulation step, QGraphicsItem's position and rotation are updated according to the item shape's.
    """

    __slots__ = ("timer", "pressed_keys", "just_pressed_key", "just_pressed_mouse_button",
                 "attractive_item", "attractive_item_force", "attractive_item_radius",
                 "central_item", "player_item", "items_to_remove", "items_to_set_kinematic",
                 "kinematic_items", "main_window", "main_view", "time", "tracing_item",
                 "trace_counter", "trace_prev_position", "actions_by_single_key",
                 "actions_by_repeat_key", "dt_s")

    trace_pen = QPen(Qt.white)
    trace_pen.setWidth(0)

    def __init__(self):
        global space
        space = self
        pymunk.Space.__init__(self)
        QGraphicsScene.__init__(self)
        # TODO
        self.setSceneRect(-2e6, -2e6, 4e6, 4e6)
        # self.setSceneRect(-2e3,-2e3,4e3,4e3)
        self.setBackgroundBrush(QBrush(Qt.black))
        self.timer = QTimer()
        self.timer.timeout.connect(self._timer_event)
        self.pressed_keys = set()
        self.just_pressed_key = None
        self.keyboard_modifiers = 0
        self.just_pressed_mouse_button = None
        self.info = ""
        self.attractive_item = None
        self.attractive_item_force = None
        self.attractive_item_radius = None
        self.central_item = None
        self.player_item = None
        self.items_to_remove = set()
        self.items_to_set_kinematic = set()
        self.kinematic_items = []
        self.main_window = MainWindow(self)
        self.main_view = self.main_window.main_view
        self.time = 0.0
        self.dt_s = None
        self.tracing_item = None
        self.trace_counter = None
        self.trace_prev_position = None
        self.actions_by_single_key = {}
        self.actions_by_repeat_key = {}
        self.do_initial_setup()
        if HIDE_CURSOR:
            app.setOverrideCursor(Qt.BlankCursor)
        Sound.init()
        # if Beep is not None:
        #     self.init_sound()

    # def init_sound(self):
    #     self.message_queue = queue.Queue()
    #     self.sound_tread = threading.Thread(target=self.sound_thread_function, daemon=True)
    #     self.sound_tread.start()
    #     # for _ in range(10):
    #     #     threading.Thread(target=self.sound_thread_function, daemon=True).start()
    #
    # def beep(self, frequency, duration):
    #     if Beep is not None:
    #         self.message_queue.put((frequency, duration))
    #
    # def sound_thread_function(self):
    #     while True:
    #         #PlaySound("explosion1.wav", SND_ASYNC | SND_FILENAME)
    #         a = self.message_queue.get()
    #         PlaySound("shoot1.wav", SND_FILENAME | SND_ASYNC)
    #         # Beep(*self.message_queue.get(), SND_ASYNC)

    def add_key_mapping(self, actions_by_single_key, actions_by_repeat_key):
        self.actions_by_single_key.update(actions_by_single_key)
        self.actions_by_repeat_key.update(actions_by_repeat_key)

    def increase_speed(self):
        self.dt_s += DELTA_ELAPSE

    def decrease_speed(self):
        if self.dt_s >= DELTA_ELAPSE:
            self.dt_s -= DELTA_ELAPSE

    def set_central_item(self, item):
        self.central_item = item
        self.main_view.recenter(with_rotation=False)

    def set_player_item(self, item):
        self.player_item = item

    def set_attractive_item(self, item, force, radius):
        self.attractive_item = item
        self.attractive_item_force = force
        self.attractive_item_radius = radius

    def center_view_on_central_item(self, with_rotation, permanent):
        self.main_view.center_on_item(self.central_item, with_rotation, permanent, False)

    def center_view_on_player(self, with_rotation, permanent):
        self.main_view.center_on_item(self.player_item, with_rotation, permanent, True)

    def toggle_trace(self, item):
        if self.tracing_item is item:
            self.tracing_item = None
        else:
            self.tracing_item = item
        self.trace_counter = 0

    def show(self):
        # self.main_window.setWindowFlags(Qt.CustomizeWindowHint | Qt.FramelessWindowHint)
        # self.main_window.showFullScreen()
        self.main_window.show()
        # self.main_window.main_view.recenter(with_rotation=False)
        self.main_view.setTransformationAnchor(QGraphicsView.NoAnchor)

    def start(self, dt_s=TIMER_ELAPSE):
        self.dt_s = dt_s
        self.timer.start(int(dt_s * 1e3))
        sys.exit(app.exec_())

    def stop(self):
        self.timer.stop()

    def close(self):
        self.stop()
        self.main_window.close()

    def toggle_help(self):
        self.display_help = not self.display_help

    def do_initial_setup(self):
        pass

    def do_timer_event(self):
        pass

    def do_mouse_press_event(self, position, button):
        pass

    def do_key_press_event(self, key):
        pass

    def _timer_event(self):
        Item.remove_transient_items()
        self.treat_kinematic_items()
        if self.tracing_item:
            self.draw_trace()
        self.treat_keys_and_buttons()
        self.do_timer_event()
        for item in self.items_to_remove:
            self.remove_item(item)
        self.items_to_remove.clear()
        self.time += self.dt_s
        # pymunk simulation
        self.step(self.dt_s)
        # self.step(SIMULATION_TIME_STEP)
        for view in self.views():
            view.do_timer_event()

    def draw_trace(self):
        # tracing_item_position = self.tracing_item.position
        item_scene_position = self.tracing_item.qg_item.scenePos()
        tracing_item_position = (item_scene_position.x(), item_scene_position.y())
        if self.trace_counter == 0:
            self.trace_prev_position = tracing_item_position
            self.trace_counter = +1
        elif self.trace_counter == +TRACE_LENGTH:
            if tracing_item_position != self.trace_prev_position:
                (x0, y0) = tracing_item_position
                (x1, y1) = self.trace_prev_position
                # TODO
                qg_line_item = QGraphicsLineItem(x0, y0, x1, y1)
                qg_line_item.setPen(MQSpace.trace_pen)
                qg_line_item.setZValue(-1)
                self.addItem(qg_line_item)
                self.trace_counter = -TRACE_LENGTH
        else:
            self.trace_counter += 1

    def treat_kinematic_items(self):
        while len(self.items_to_set_kinematic) > 0:
            item = self.items_to_set_kinematic.pop()
            if item.is_alive:
                item.body_type = KINEMATIC
                for shape in item.child_shapes:
                    self.remove(shape)
                item.child_shapes = ()
                # while len(item.child_shapes) > 0:
                #    self.remove(item.child_shapes.pop())
                self.kinematic_items.append(item)
        for item in self.kinematic_items:
            item.do_update_velocity()

    def mousePressEvent(self, mouseEvent):
        self.just_pressed_mouse_button = mouseEvent.button()
        self.do_mouse_press_event((mouseEvent.scenePos().x(), mouseEvent.scenePos().y()), mouseEvent.button())

    def keyPressEvent(self, keyEvent):
        keyEvent.accept()
        if not keyEvent.isAutoRepeat():
            space.just_pressed_key = keyEvent.key()
            self.pressed_keys.add(space.just_pressed_key)
        space.keyboard_modifiers = int(QGuiApplication.queryKeyboardModifiers())
        self.do_key_press_event(keyEvent.key())

    def keyReleaseEvent(self, keyEvent):
        keyEvent.accept()
        if not keyEvent.isAutoRepeat():
            try:
                self.pressed_keys.remove(keyEvent.key())
            except Exception as exc:
                print(f"WARNING in keyReleaseEvent - exception raised: {exc}")

    NO_ACTION = (None, None, "")

    def treat_keys_and_buttons(self):
        self.keyboard_modifiers = int(QGuiApplication.queryKeyboardModifiers())
        self.info = None
        # call once the registered callback function associated to last key pressed, if any
        if self.just_pressed_key is not None:
            (func, args, info) = self.actions_by_single_key.get((self.keyboard_modifiers, self.just_pressed_key),
                                                                MQSpace.NO_ACTION)
            if func is not None:
                self.info = info
                func(*args)
        # call the registered callback function(s) associated to currently pressed key(s), if any
        for key in space.pressed_keys:
            (func, args, info) = self.actions_by_repeat_key.get((self.keyboard_modifiers, key), MQSpace.NO_ACTION)
            if func is not None:
                self.info = info
                func(*args)
        # call once the registered callback function associated to last mouse button pressed, if any
        if self.just_pressed_mouse_button is not None:
            (func, args, info) = self.actions_by_single_key.get((self.keyboard_modifiers | MOUSE_BUTTON,
                                                                 self.just_pressed_mouse_button),
                                                                MQSpace.NO_ACTION)
            if func is not None:
                func(*args)
            self.just_pressed_mouse_button = None
        # call the registered callback function associated to currently pressed mouse button, if any
        (func, args, info) = self.actions_by_repeat_key.get((self.keyboard_modifiers | MOUSE_BUTTON,
                                                             int(QApplication.mouseButtons())), MQSpace.NO_ACTION)
        if func is not None:
            func(*args)

    def get_cursor_position(self):
        # position = self.main_view.mapFromGlobal(QCursor().pos())
        # position = self.main_view.mapToScene(QCursor().pos())
        # position = self.main_view.mapToScene(QCursor().pos().x(), -QCursor().pos().y())
        # position = self.main_view.mapToScene(self.main_view.viewport().mapFromGlobal(QCursor().pos()))
        position = self.main_view.mapToScene(self.main_view.mapFromGlobal(QCursor().pos()))
        # position = self.main_view.viewport().mapToGlobal(QCursor().pos())
        return (position.x(), position.y())

    def add_item(self, item):
        if not item.is_alive:
            if item.body_type != STATIC:
                self.add(item)
            self.addItem(item.qg_item)
            """
            if not (item.body_type == KINEMATIC and item.is_airy):
                for shape in item.child_shapes:
            """
            # self.add(*item.child_shapes)
            for shape in item.child_shapes:
                self.add(shape)
            item.is_alive = True
            # TODO remove handler in remove_item
            if item.collision_function is not None:
                # collision_handler = space.add_wildcard_collision_handler(id(item.__class__))
                # collision_handler.begin = item.collision_function
                space.on_collision(id(item.__class__), None, begin=item.collision_function)

    def remove_item(self, item):
        if item.is_alive:
            """
            if not (item.body_type == KINEMATIC and item.is_airy):
                for shape in item.child_shapes:
            """
            if self.tracing_item is item:
                self.toggle_trace(item)
            for shape in item.child_shapes:
                self.remove(shape)
            # TODO: check this
            # if False and isinstance(item, CompoundItemDecomposable):
            #    for child_item in item.child_items:
            #        self.remove_item(child_item)
            self.remove(item)
            self.removeItem(item.qg_item)
            item.is_alive = False
            item.do_finalize()

    def add_circle_item(self, position, angle, radius, **kwargs):
        circle_item = CircleItem(position, angle, radius, **kwargs)
        self.add_item(circle_item)
        return circle_item

    def add_rect_item(self, position, angle, size, **kwargs):
        rect_item = RectItem(position, angle, size, **kwargs)
        self.add_item(rect_item)
        return rect_item

    def add_text_item(self, position, angle, text, font_size=None, font_family=None, **kwargs):
        text_item = TextItem(position, angle, text, font_size, font_family, **kwargs)
        self.add_item(text_item)
        return text_item

    def add_polygon_item(self, position, angle, vertices, **kwargs):
        polygon_item = PolygonItem(position, angle, vertices, **kwargs)
        self.add_item(polygon_item)
        return polygon_item

    def add_segment_item(self, position, angle, size, color, **kwargs):
        segment_item = SegmentItem(position, angle, size, color, **kwargs)
        self.add_item(segment_item)
        return segment_item

    def add_pixmap_item(self, position, angle, pixmap_filename, rounded=False, **kwargs):
        pixmap_item = PixmapItem(position, angle, pixmap_filename, rounded, **kwargs)
        self.add_item(pixmap_item)
        return pixmap_item

    def add_compound_item(self, position, angle, *shaqes, **kwargs):
        compound_item = CompoundItem(position, angle, *shaqes, **kwargs)
        self.add_item(compound_item)
        return compound_item

    def dismantle_compound_item(self, compound_item, recursive=False):
        assert isinstance(compound_item, CompoundItemDecomposable)
        self.remove_item(compound_item)
        for item in compound_item.child_items:
            qg_item_pos = item.qg_item.scenePos()
            item.position = (qg_item_pos.x(), qg_item_pos.y())
            item.body.angle += compound_item.angle
            item.qg_item.setRotation(degrees(item.body.angle))
            item.velocity = compound_item.velocity_at_world_point(item.position)
            for shape in item.child_shapes:
                shape.body = item
            self.add_item(item)
            if recursive and isinstance(item, CompoundItemDecomposable):
                self.dismantle_compound_item(item, recursive=True)
        for item in compound_item.child_items:
            compound_item.qg_item.removeFromGroup(item.qg_item)


class MainWindow(QMainWindow):

    def __init__(self, space):
        QMainWindow.__init__(self)
        self.installEventFilter(self)
        # self.setWindowFlags(Qt.CustomizeWindowHint | Qt.FramelessWindowHint)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)
        self.main_view = View(self, space)
        self.setCentralWidget(self.main_view)
        # self.setCursor(Qt.BlankCursor)
        self.main_view.setFocus(Qt.OtherFocusReason)


class View(QGraphicsView):

    def __init__(self, parent, space1):
        QGraphicsView.__init__(self, space1, parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setInteractive(False)
        # screen_geometry = QApplication.desktop().screenGeometry()
        # self.setWindowFlags(Qt.CustomizeWindowHint | Qt.FramelessWindowHint)
        self.setFrameStyle(QFrame.NoFrame)
        self.setRenderHints(QPainter.Antialiasing)
        # TODO
        # self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        # THIS TRANSLATES THE VIEW AT STARTUP  
        # self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.h_scrollbar = self.horizontalScrollBar()
        self.v_scrollbar = self.verticalScrollBar()
        self.rotation = 0.0
        # self.central_item = None
        # self.is_view_centering_on_player = False
        self.view_center_item = None
        self.view_center_with_rotation = False
        self.view_center_with_centering = False

    def _translate(self, dx, dy):
        # self.setTransformationAnchor(QGraphicsView. NoAnchor)
        self.translate(dx, dy)
        # View.translate(self, dx, dy)

    def do_timer_event(self):
        if self.view_center_item is not None:
            self.center_on(self.view_center_item, self.view_center_with_rotation, self.view_center_with_centering)

    def center_on_item(self, item, with_rotation, permanent, with_centering):
        if permanent:
            if self.view_center_item is item:
                self.view_center_item = None
                self.view_center_with_rotation = None
            else:
                self.view_center_item = item
                self.view_center_with_rotation = with_rotation
            self.view_center_with_centering = with_centering
        else:
            self.view_center_item = None
            self.view_center_with_rotation = None
            self.center_on(item, with_rotation, with_centering)

    def center_on(self, item, with_rotation, with_centering):
        if item is not None:
            if with_rotation:
                rotation = -item.qg_item.rotation()
                self.rotate(-self.rotation + rotation)
                self.rotation = rotation
            if with_centering:
                self.centerOn(item.qg_item)

    def recenter(self, with_rotation):
        if space.central_item is not None:
            self.center_on(space.central_item, with_rotation, True)

    def wheelEvent(self, event):
        self.zoom(event.angleDelta().y() / 100.0)

    def zoom(self, f):
        pos_view1 = self.mapFromGlobal(QCursor.pos())
        pos_scene = self.mapToScene(pos_view1)
        if f < 0.0:
            f = -1.0 / f
        self.scale(f, f)
        pos_view2 = self.mapFromScene(pos_scene)
        dx_view = pos_view2.x() - pos_view1.x()
        dy_view = pos_view2.y() - pos_view1.y()
        self.h_scrollbar.setValue(self.h_scrollbar.value() + dx_view)
        self.v_scrollbar.setValue(self.v_scrollbar.value() + dy_view)


DYNAMIC = pymunk.Body.DYNAMIC
KINEMATIC = pymunk.Body.KINEMATIC
STATIC = pymunk.Body.STATIC

space = None
app = QApplication(sys.argv)
