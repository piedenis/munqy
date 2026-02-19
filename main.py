#--------------------------------------------------------------------------------
#   Example program using Munqy
#   (c) Pierre Denis 2021-2025
#--------------------------------------------------------------------------------
from PyQt5.QtWidgets import QLabel

WORLD_RADIUS = 350
WORLD2_RADIUS = 900
BALL_RADIUS = 100
WIND_RADIUS = 1
BULLET_RADIUS = 2
BOMB_RADIUS = 3
BOX_HSIZE = 400
BOX_VSIZE = 800
BOMB_REARM_DELAY_S = 0.5
BOMB_EXPLOSION_DELAY_S = 4.0
BULLET_REARM_DELAY_S = 0.2
BULLET_LIFETIME_S = 2.0
BULLET_SPEED = 12e2
DAMPING = 1
SEGMENT_THICKNESS = 40
GRAVITY = 600

CENTRAL_GRAVITY_FORCE_1 =  1.6e8
CENTRAL_GRAVITY_FORCE_2 = 8e8
ANGULAR_VELOCITY = 1*0.5
SPACECRAFT_STABILIZATION = True

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QRadialGradient, QBrush, QPen, QColor, QCursor
from munqy import Sound
import munqy
import sys
from math import pi, cos, sin, atan2, hypot
from random import uniform

PI2 = 2 * pi

space = None


class USpace(munqy.MQSpace):

    def __init__(self):
        self.brush2 = QBrush(QColor(120,120,250))
        self.color3 = Qt.green #QColor(180,220,180)
        self.brush3 = QBrush(self.color3)
        self.spacecraft_item = None
        self.spacecraft_item_csc = None
        self.spacecraft_item_osc = None
        self.collision_handler1 = None
        super().__init__()
        self.counter = None
        self.display_help = False
        self.label = QLabel(self.main_view)
        self.label.setStyleSheet("QLabel { font-size: 80px; color : white; }")
        # self.label.setText(256*"X")
        self.label.hide()

        Sound.say("3, 2, 1, GO!")

    def do_initial_setup(self):
        """
        radialGrad = QRadialGradient(0,0,BALL_RADIUS)
        radialGrad.setColorAt(0.00, Qt.white)
        radialGrad.setColorAt(1.00, QColor(40,40,40))
        self.brush2 = QBrush(radialGrad)
        """
        spacecraft_position = (0, -400)
        if len(sys.argv) >= 2:
            world_arg = sys.argv[1]
            if world_arg == "0":
                r = 400
                x = self.add_polygon_item(self.get_cursor_position(), 0., vertices=((0, 0), (r, 0), (r, r),
                                                                                (r//2, r), (r//2, r//2), (0, r//2)),
                                      velocity=(0, 0), density=1.25e11, brush=self.brush3)
                x._set_position((0, -650))
                x = self.add_polygon_item(self.get_cursor_position(), 0., vertices=((0, 0), (r, 0), (r, r)),
                                      velocity=(0, 0), density=1.25e11, brush=self.brush3)
                x._set_position((0, -150))
            elif world_arg == "1":
                self.gravity = (0,GRAVITY)
                self.damping = DAMPING
                W = 1800
                W2 = W / 2.
                self.segments = ( ((  10,  -460), (1000,  -410)),
                                  (( 900,  -200), (W-10,  -600)),
                                  ((  10,   -10), (  10, -1000)),
                                  ((  10,   -10), (   W,   -10)),
                                  ((   W,   -10), (   W, -1000)))
                for (p1,p2) in self.segments:
                    (x1, y1) = p1
                    (x2, y2) = p2
                    length = hypot(x2-x1, y2-y1)
                    p = (-W2+(x1+x2)/2., W2-400+(y1+y2)/2.)
                    a = atan2(y2-y1, x2-x1)
                    self.add_segment_item(p, a, size=(length, SEGMENT_THICKNESS),
                                          color=Qt.darkGray,
                                          elasticity=1, friction=0.6,
                                          body_type=munqy.STATIC)
                self.add_item(Platform((600, -250), 0, (200, 20), ay=400.0))
                self.add_item(Platform((230, 80), 0, (240, 10), ax=60.0))
            elif world_arg == "2":
                brush1 = QBrush(QColor(30, 30, 55))
                n = 120
                k = pi / (n - 1)
                semicircle_vertices1 = tuple(
                    (-WORLD2_RADIUS * sin(k * t), WORLD2_RADIUS * cos(k * t)) for t in range(1, n - 2))
                semicircle_vertices2 = tuple(
                    (+WORLD2_RADIUS * sin(k * t), WORLD2_RADIUS * cos(k * t)) for t in range(n - 3, 2, -1))
                semicircle_shaqe1 = munqy.PolygonShaqe(semicircle_vertices1, density=1e13, brush=brush1,
                                                       elasticity=1, friction=0.6)
                semicircle_shaqe2 = munqy.PolygonShaqe(semicircle_vertices2, density=1e13, brush=brush1,
                                                       elasticity=1, friction=0.6)
                attractive_item = self.add_compound_item((0., 0.), 0., semicircle_shaqe1, semicircle_shaqe2,
                                                         angular_velocity=ANGULAR_VELOCITY)
                self.set_attractive_item(attractive_item, CENTRAL_GRAVITY_FORCE_2, WORLD2_RADIUS)
                self.set_central_item(attractive_item)
            elif world_arg[-1] in ("3", "4"):
                radial_grad = QRadialGradient(0, 0, WORLD_RADIUS)
                radial_grad.setColorAt(0.00, Qt.black)
                radial_grad.setColorAt(0.85, QColor(0, 0, 80))
                radial_grad.setColorAt(1.00, QColor(0, 0, 128))
                brush1 = QBrush(radial_grad)
                # circle_shaqe1 = self.add_circle_item((0., 0.), 0., WORLD_RADIUS, density=1e13, brush=brush1,
                #                                      #velocity=(0., 0.), angular_velocity=ANGULAR_VELOCITY,
                #                                      elasticity=1, friction=0.6,
                #                                      body_type=munqy.STATIC,)
                circle_shaqe1 = munqy.CircleShaqe(WORLD_RADIUS, density=1e13, brush=brush1,
                                                        elasticity=1, friction=1.6)
                                                        #body_type=munqy.STATIC)
                if world_arg[-1] == "3":
                    brush1 = QBrush(QColor(150, 150, 250))
                    circle_shaqe2 = munqy.CircleShaqe(10, offset=(WORLD_RADIUS - 20, 0), density=1e13, brush=brush1,
                                                      is_airy=True)
                    attractive_item = self.add_compound_item((0., 0.), 0., circle_shaqe1, circle_shaqe2,
                                                             angular_velocity=4*ANGULAR_VELOCITY)
                else:
                    attractive_item = self.add_compound_item((0., 0.), 0., circle_shaqe1,
                                                             is_airy=True,
                                                             body_type=munqy.STATIC)
                self.set_attractive_item(attractive_item, CENTRAL_GRAVITY_FORCE_1, WORLD_RADIUS)
                self.set_central_item(attractive_item)
            elif world_arg == "5":
                matrix = ("..............................................................................",
                          ".WWWWWWWWWWWWWWW.WWWWWWWWW.........WWWWWWWWWWWW...............................",
                          ".WWWWWWWWWWWWWWW.WWWWWWWWW.........WWWW....WWWW...............................",
                          ".WWWWWWWWWWWWWWW.WWWWWWWWW.........WWWW.WW.WWWW...............................",
                          ".WWWWWWWWWWWWWWW.WWWWWWWWW.................WWWW.............WWWWWWWWWWWWWWWWW.",
                          ".WWWW.................WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW.",
                          ".WWWW..W..W..W........WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW.",
                          ".WWWW.....W..W.......................WWWWWWWWW..............WWWWWWWWWWWWWWWWW.",
                          ".WWWW.... WWWW......WWWWWWWWWWWWWWW..WWWWWWWWW..............WWWWWWWWWWWWWWWWW.",
                          ".WWWW.WWWWWWWWWWWWWWWWWWWW...... WW..WWWWWWWWWWWWWWWW.......WWWWWWWWWWWWWWWWW.",
                          ".WWWW.WWWWWWWWW..WWWWWWWWW.......WW.........................WWWWWWWWWWWWWWWWW.",
                          ".WWWW.WWWWWWWWW..WWWWWWWWW.......WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW.",
                          ".WWWW.WWWWWWWWWW.WWWWWWWWW....................................................",
                          "..............................................................................")

                matrix2 = ("wwwwwwwwwwwwwwwwwwwwwwwww",
                          "W.......................W",
                          "W........WWW............W",
                          "W........WWW............W",
                          "W.......................W",
                          "wwwwwwwwwwwwwwwwwwwwwwwww",
                          )

                central_item = munqy.CompoundItem.build_from_matrix((-500, -500), 0, matrix, "W", block_size=50,
                                                                    brush=QBrush(Qt.darkGray), elasticity=1., soft=False,
                                                                    friction = 1.5,
                                                                    body_type=munqy.KINEMATIC, angular_velocity=0.05)
                # self.add_item(munqy.CompoundItem.build_from_matrix((-500, -500), 0, matrix, "w", block_size=50,
                #                                                     brush=QBrush(Qt.darkGray), elasticity=1., soft=False,
                #                                                     body_type=munqy.KINEMATIC, angular_velocity=0.00))
                self.add_item(central_item)
                self.set_central_item(central_item)
                self.gravity = (0, GRAVITY)
                # self.set_attractive_item(central_item,CENTRAL_GRAVITY_FORCE_2,WORLD2_RADIUS)
            elif world_arg == "6":
                with open("resources/siriusbee_levels.txt", 'r') as f:
                    matrix = f.readlines()
                central_item = munqy.CompoundItem.build_from_matrix((-500,-500),0,matrix,"W",block_size=20,
                                                                    brush=QBrush(Qt.darkGray),elasticity=1.,soft=False,
                                                                    body_type=munqy.KINEMATIC,angular_velocity=20.00)
                # self.add_item(munqy.CompoundItem.build_from_matrix((-500,-500),0,matrix,"w",block_size=20,
                #                                                     brush=QBrush(Qt.darkGray),elasticity=1.,soft=False,
                #                                                     body_type=munqy.KINEMATIC,angular_velocity=0.00))
                self.add_item(central_item)
                self.set_central_item(central_item)
                self.gravity = (0, GRAVITY)
            elif world_arg == "7":
                global SPACECRAFT_STABILIZATION
                SPACECRAFT_STABILIZATION = False
                brush1 = QBrush(QColor(30, 30, 55))

                # TODO: bug Pymunk 7 ?    moment becomes -inf when n >= 107   if precision=0
                #       This was OK in pymunk 6
                n = 360
                k = 2*pi / n
                r1 = 2*WORLD2_RADIUS
                r2 = r1 - 500
                ring_vertices = tuple((-r1 * sin(k * t), r1 * cos(k * t)) for t in range(n)) \
                              + tuple((-r2 * sin(k * t), r2 * cos(k * t)) for t in range(n - 1, -1, -1))
                              #+ tuple((-r2 * sin(k * t), r2 * cos(k * t)) for t in range(n-1, -1, -1))
                #ring_vertices = ((0,0), (0,400), (400,400), (200, 0))[::-1]
                ring_item = self.add_polygon_item((0., 0.), 0., ring_vertices, angular_velocity=ANGULAR_VELOCITY,
                                                  moment=float('inf'),
                                                  #moment=100,
                                                  #velocity=(0, 0),
                                                  density=1e13, brush=brush1, elasticity=0.1, friction=1.4)
                self.add_item(ring_item)
                self.set_central_item(ring_item)
            elif world_arg == "8":
                self.gravity = (0, GRAVITY)
                spacecraft_position = self.load_level("resources/level.svg")


        if world_arg == "P3":
            munqy.SIMULATION_TIME_STEP = 2e-3  # in sec
            munqy.HIDE_CURSOR = True
            spacecraft_item_csc = SpacecraftItemCSC((0, -10), 0., time=self.time)
            spacecraft_item_osc = SpacecraftItemOSC((0, +10), 0., time=self.time)
            spacecraft_item = SpacecraftItemP3(
                (-180, 0), 0.,
                spacecraft_item_csc,
                spacecraft_item_osc,
                velocity=(0, -1400))
            spacecraft_item.thrust_up = \
            spacecraft_item.thrust_down = \
            spacecraft_item.thrust_left =  \
            spacecraft_item.thrust_right =  \
            spacecraft_item.fire = \
            spacecraft_item.drop_bomb = lambda: None
        else:
            # spacecraft_item = SpacecraftItem((0,-400),0.,"spacecraft.png",
            spacecraft_item = SpacecraftItem(spacecraft_position, 0., time=self.time,
                                                  velocity=(0., 0.), angular_velocity=0.0)
        self.add_item(spacecraft_item)
        spacecraft_item.center_of_gravity = (0, 0)
        #spacecraft_item.moment = 100.0 * spacecraft_item.moment
        if world_arg == "P3":
            self.set_player_item(spacecraft_item_csc)
        else:
            self.set_player_item(spacecraft_item)
        self.spacecraft_item = spacecraft_item
        self.center_view_on_player(False, True)

        # TODO
        #self.collision_handler1 = self.add_wildcard_collision_handler(id(Bullet))
        ## self.collision_handler1 = self.add_collision_handler(id(Bullet),id(munqy.CircleItem))
        #self.collision_handler1.post_solve = self.collides
        self.on_collision(id(Bullet), None, begin=self.collides)

        # self.kinematic_items = []
        actions_by_single_key = {
            (Qt.NoModifier, Qt.Key_Escape)       : (self.close, (),                                   "quit"                                               ),
            (Qt.NoModifier, Qt.Key_H)            : (self.toggle_help, (),                             "toggle help"                                        ),
            (Qt.ShiftModifier, Qt.Key_X)         : (self.center_view_on_player, (False, True),        "toggle view centering on spacecraft"                ),
            (Qt.ShiftModifier, Qt.Key_W)         : (self.center_view_on_central_item, (True, True),   "toggle view centering on central item with rotation"),
            (Qt.ShiftModifier, Qt.Key_C)         : (self.center_view_on_central_item, (False, True),  "toggle view centering on central item"              ),
            (Qt.NoModifier, Qt.Key_Minus)        : (self.decrease_speed, (),                          "decrease simulation speed"                          ),
            (Qt.NoModifier, Qt.Key_Plus)         : (self.increase_speed, (),                          "increase simulation speed"                          ),
            (Qt.NoModifier, Qt.Key_Equal)        : (self.increase_speed, (),                          "increase simulation speed"                          ),
            (Qt.NoModifier, Qt.Key_S)            : (self.separate_spacecrafts, (),                    "separate spacecrafts"                               ),
            (Qt.ShiftModifier|munqy.MOUSE_BUTTON, Qt.LeftButton)  : (self.drop_item3, (),             "drop new item type #3"                              ),
            (Qt.ShiftModifier|munqy.MOUSE_BUTTON, Qt.RightButton) : (self.drop_item4, (),             "drop new item type #4"                              )
        }

        actions_by_repeat_key = {
            (Qt.NoModifier, Qt.Key_A)            : (self.main_view.zoom, (+1.01,),                    "zoom in"                                            ),
            (Qt.NoModifier, Qt.Key_Q)            : (self.main_view.zoom, (-1.01,),                    "zoom out"                                           ),
            (Qt.NoModifier, Qt.Key_X)            : (self.center_view_on_player, (False, False),       "center view on spacecraft"                          ),
            (Qt.NoModifier, Qt.Key_W)            : (self.center_view_on_central_item, (True, False),  "center view on central item with rotation"          ),
            (Qt.NoModifier, Qt.Key_C)            : (self.center_view_on_central_item, (False, False), "center view on central item"                        ),
            (Qt.ShiftModifier, Qt.Key_Up)        : (self.main_view._translate,( 0, +4),               "move view up"                                       ),
            (Qt.ShiftModifier, Qt.Key_Down)      : (self.main_view._translate,( 0, -4),               "move view down"                                     ),
            (Qt.ShiftModifier, Qt.Key_Left)      : (self.main_view._translate,(+4,  0),               "move view left"                                     ),
            (Qt.ShiftModifier, Qt.Key_Right)     : (self.main_view._translate,(-4,  0),               "move view right"                                    ),
            (munqy.MOUSE_BUTTON, Qt.LeftButton)  : (self.drop_item1, (),                              "drop new item type #1"                              ),
            (munqy.MOUSE_BUTTON, Qt.RightButton) : (self.drop_item2, (),                              "drop new item type #2"                              ),
        }
        self.add_key_mapping(actions_by_single_key, actions_by_repeat_key)

    def set_player_item(self, item):
        if self.player_item is not None:
            if self.main_view.view_center_item is self.player_item:
                self.main_view.view_center_item = item
            if self.tracing_item is self.player_item:
                self.tracing_item = item
        super().set_player_item(item)
        actions_by_single_key = {
            (Qt.NoModifier, Qt.Key_T)            : (self.toggle_trace, (item,), "toggle trace"                 ),
        }
        actions_by_repeat_key = {
            (Qt.NoModifier, Qt.Key_Up)           : (item.thrust_up, (),          "trust up / across-track"     ),
            (Qt.NoModifier, Qt.Key_Down)         : (item.thrust_down, (),        "trust down / across-track"   ),
            (Qt.NoModifier, Qt.Key_Left)         : (item.thrust_left,(),         "trust left / along-track"    ),
            (Qt.NoModifier, Qt.Key_Right)        : (item.thrust_right, (),       "trust right / along-track"   ),
            (Qt.ControlModifier, Qt.Key_Up)      : (item.thrust_up, (),          "trust up / across-track"     ),
            (Qt.ControlModifier, Qt.Key_Down)    : (item.thrust_down, (),        "trust down / across-track"   ),
            (Qt.ControlModifier, Qt.Key_Left)    : (item.thrust_left, (),        "trust left / along-track"    ),
            (Qt.ControlModifier, Qt.Key_Right)   : (item.thrust_right, (),       "trust right / along-track"   ),
            (Qt.ControlModifier, Qt.Key_Control) : (item.fire, (),               "fire"                        ),
            (Qt.NoModifier, Qt.Key_Space)        : (item.drop_bomb, (),          "drop bomb"                   ),
        }
        self.add_key_mapping(actions_by_single_key, actions_by_repeat_key)

    def collides(self, arbiter, space, data):
        """
        #print(arbiter.shapes)
        for shape in arbiter.shapes:
            #self.remove_item(shape.body)
            self.items_to_remove.add(shape.body)
        """
        Sound.hit1.play_once()
        (particle_shape, shape) = arbiter.shapes
        self.items_to_remove.add(particle_shape.body)
        if isinstance(shape.body, (munqy.CircleItem, munqy.PolygonItem)):
            Sound.hit3.play_once()
            #self.items_to_remove.add(shape.body)
            shape.body.set_transient(0.25, with_fading=True)
            # NOK - shall be defered
            #shape.body.body_type = munqy.KINEMATIC
            uspace.items_to_set_kinematic.add(shape.body)
            #shape.body.is_airy = True
        #return True

    """
    def do_key_press_event(self,key):
        try:
            self.add_text_item(self.get_cursor_position(),0.0,chr(key),font_size=20,
                                body_type = munqy.KINEMATIC, is_airy = True,
                                velocity=(uniform(-20,20),uniform(-20,20)),
                                angular_velocity=uniform(-1,1),
                                brush=self.brush2).set_transient(1,with_fading=True)
        except:
            pass
    """
    
    def drop_item1(self):
        self.add_circle_item(self.get_cursor_position(),0.,radius=1,
                             velocity=(uniform(-200,200), uniform(-200,200)), elasticity=0.1,
                             density=0.25e10, brush=self.brush2)

    def drop_item3(self):
        self.add_circle_item(self.get_cursor_position(), 0., radius=uniform(10, 40),
                             velocity=(uniform(-200, 200), uniform(-200, 200)), elasticity=0.1,
                             density=0.25e11, brush=self.brush2)

    def drop_item2(self):
        self.add_rect_item(self.get_cursor_position(), 0., size=(uniform(4, 16),uniform(4, 16)),
                            # body_type = munqy.KINEMATIC, is_airy = True,
                            velocity=(uniform(-200, 200), uniform(-200, 200)),
                            angular_velocity=uniform(-2, 2),
                            density=1.25e10,
                            brush=self.brush3, duration_s=8, with_fading=True)
        
    def drop_item4(self):
        # self.add_rect_item(self.get_cursor_position(),0.,size=(uniform(40,100),uniform(40,100)),
        #                     #body_type = munqy.KINEMATIC, is_airy = True,
        #                     velocity=(uniform(-200,200),uniform(-200,200)),
        #                     angular_velocity=uniform(-2,2),
        #                     density=1.25e10,
        #                     brush=self.brush3,duration_s=8,with_fading=True)
        # r.velocity = (uniform(-200,200),uniform(-200,200))
        # self.kinematic_items.append(r)
        # self.add_segment_item((position.x(), position.y()),0.,size=(uniform(4,16),uniform(4,16)),
        #                       velocity=(uniform(-200,200),uniform(-200,200)),density=1.25e10,color=self.color3)
        d = \
        self.add_polygon_item(self.get_cursor_position(), 0., vertices=((0, 0), (+40, 0), (+40, +40), (+20, +40), (+20, +20), (0, +20)),
                              friction=0.5,
                              velocity=(uniform(-200,200), uniform(-200,200)), density=1.25e11,brush=self.brush3)
        # print(d.center_of_gravity)
        # d.center_of_gravity = (0, 0)
    def separate_spacecrafts(self):
        if self.spacecraft_item is not None and isinstance(self.spacecraft_item, munqy.CompoundItemDecomposable):
            self.dismantle_compound_item(self.spacecraft_item)
            (self.spacecraft_item_csc, self.spacecraft_item_osc) = self.spacecraft_item.child_items
            self.set_player_item(self.spacecraft_item_csc)
            self.spacecraft_item = self.spacecraft_item_csc

    key_character_by_key_code =  { Qt.Key_Up    : '🡑',
                                   Qt.Key_Down  : '🡓',
                                   Qt.Key_Right : '🡒',
                                   Qt.Key_Left  : '🡐' }

    key_character_by_key_modifier =  { Qt.ShiftModifier   : 'Shift',
                                       Qt.ControlModifier : 'Ctrl',
                                       Qt.AltModifier     : 'Alt' }

    def do_timer_event(self):
        if self.display_help and self.just_pressed_key is not None and self.info is not None:
            s = []
            if self.keyboard_modifiers != 0:
                m = USpace.key_character_by_key_modifier.get(self.keyboard_modifiers, "?")
                s.append(m)
            if self.just_pressed_key is not None:
                try:
                    c = chr(self.just_pressed_key)
                except:
                    c = USpace.key_character_by_key_code.get(self.just_pressed_key, str(self.just_pressed_key))
                s.append(c)
            self.label.setText("+".join(s)+": "+self.info)
            self.label.adjustSize()
            self.label.show()
            self.counter = 0
        if self.counter is not None:
            if self.counter == 499:
                self.label.hide()
                self.counter = None
            else:
                self.counter += 1
        self.just_pressed_key = None
        self.keyboard_modifiers = 0
        if SPACECRAFT_STABILIZATION:
            if self.spacecraft_item is not None:
                self.spacecraft_item.stabilize()
            if self.spacecraft_item_osc is not None:
                self.spacecraft_item_osc.stabilize()

    """
    def do_timer_event(self):
        if self.counter == 0:
            if self.display_help and self.info is not None:
                s = []
                if self.keyboard_modifiers != 0:
                    m = USpace.key_character_by_key_modifier.get(self.keyboard_modifiers, "?")
                    s.append(m)
                if self.just_pressed_key is not None:
                    try:
                        c = chr(self.just_pressed_key)
                    except:
                        c = USpace.key_character_by_key_code.get(self.just_pressed_key, str(self.just_pressed_key))
                    s.append(c)
                self.label.setText("+".join(s)+": "+self.info)
                self.label.adjustSize()
                self.label.show()
                self.counter = 1
        elif self.counter == 500:
            self.label.hide()
            self.counter = 0
        else:
            self.counter += 1
        self.just_pressed_key = None
        self.keyboard_modifiers = 0
        if self.spacecraft_item is not None:
            self.spacecraft_item.stabilize()
        if self.spacecraft_item_osc is not None:
            self.spacecraft_item_osc.stabilize()
    """

class AbstractSpacecraftItem(munqy.CompoundItem):

    wind_brush = QBrush(QColor(255, 255, 200))

    def __init__(self, *args, **kwargs):
        munqy.CompoundItem.__init__(self, *args, **kwargs)

    def activate_thruster(self, local_force, local_position):
        (fx, fy) = local_force
        if fx == 0 and fy == 0:
            return
        self.apply_impulse_at_local_point(local_force, local_position)
        (rx, ry) = local_position
        (x, y) = self.position
        (vx, vy) = self.velocity
        a = self.angle
        (dx, dy) = (cos(a), sin(a))
        position = (x + rx * dx + ry * dy, y + rx * dy - ry * dx)
        a += atan2(-fy, -fx) + uniform(-0.2, 0.2)
        (dx, dy) = (cos(a), sin(a))
        v = uniform(0.5, 1.5) * 1e-13 * hypot(fx, fy)
        velocity = (vx + v * dx, vy + v * dy)
        uspace.add_item(ParticleItem(position, velocity,
                                     brush=AbstractSpacecraftItem.wind_brush,
                                     #density=8.0e12, elasticity=0.65, friction=1,
                                     density=1, elasticity=0, friction=0,
                                     duration_s=0.2, with_fading=True))

    def stabilize(self):
        # TODO
        # space = self.qg_item.scene()
        # space = munqy.space
        if uspace.attractive_item is not None:
            (x,y) = self.position
            (cx,cy) = uspace.attractive_item.position
            dx = x - cx
            dy = y - cy
            target_angle = atan2(+dx,-dy)         
        else:
            target_angle = 0.0
        a = self.angle % PI2
        if a > pi:
            a -= PI2
        da = target_angle - a
        if da > pi:
            da = -PI2 + da
        elif da < -pi:
            da = +PI2 + da
        self.torque = +1e19*da - 0.09e19 * self.angular_velocity

    def thrust_up(self):
        pass

    def thrust_down(self):
        pass

    def thrust_left(self):
        pass

    def thrust_right(self):
        pass

    def fire(self):
        pass

    def drop_bomb(self):
        pass


class SpacecraftItem(AbstractSpacecraftItem):
    shape_pen = QPen(QColor(100, 100, 100))
    shape_pen.setJoinStyle(Qt.RoundJoin)
    fire_brush = QBrush(Qt.yellow)

    def __init__(self, position, angle, time, **kwargs):
        hull_shaqe = munqy.SegmentShaqe((16, 16), Qt.gray,
                                        density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        # battery_shaqe = munqy.RectShaqe(size=(8,4), offset=(8,4),
        #                                brush=QBrush(Qt.darkGray),
        #                                is_airy=True, **kwargs)
        battery_shaqe = munqy.SegmentShaqe((8, 4), Qt.darkGray, offset=(8, 4),
                                           is_airy=True, **kwargs)
        cannon_shaqe = munqy.SegmentShaqe((12, 2), "lightgray", offset=(12, 4),
                                          density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        # reactor1_shaqe = munqy.PolygonShaqe(((-5,6),(-1,6),(-1,9),(-5,9)),
        reactor_d1_shaqe = munqy.RectShaqe(size=(5, 4), offset=(-3, +7.5),
                                            brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                            density=1e12, elasticity=0.45, friction=0.2, **kwargs)
        #reactor2_shaqe = munqy.PolygonShaqe(((1,6),(5,6),(5,9),(1,9)),
        reactor_d2_shaqe = munqy.RectShaqe(size=(5, 4), offset=(+3, +7.5),
                                            brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                            density=1e12, elasticity=0.45, friction=0.2, **kwargs)
        reactor_u_shaqe = munqy.RectShaqe(size=(4, 3), offset=(0, -7.5),
                                          brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                          density=1e12,elasticity=0.45, friction=2.9, **kwargs)
        reactor_l_shaqe = munqy.RectShaqe(size=(3, 4), offset=(-16, 0),
                                          brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                          density=1e12,elasticity=0.45, friction=2.9, **kwargs)
        reactor_r_shaqe = munqy.RectShaqe(size=(3,4), offset=(+16, 0),
                                          brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                          density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        # cockpit_shaqe = munqy.CircleShaqe(4.0, (9.0,-3.0), brush=QBrush(QColor(250,250,255)),
        #                                  is_airy=True)
        cockpit_shaqe = munqy.CircleShaqe(5.0, (9.0, -4.0), brush=QBrush(QColor("powderblue")),
                                          pen=QPen(Qt.darkGray, 1),
                                          density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        # text_shaqe = munqy.TextShaqe("munqy",font_size=4, font_family="Bauhaus 93", offset=(0,2),
        text_shaqe = munqy.TextShaqe("Ω", font_size=5, offset=(-4, -2.5),
                                     brush=QBrush(Qt.white),
                                     is_airy=True)
        line_shaqe = munqy.SegmentShaqe((15, 6), offset=(-2, -2), color_name=Qt.darkGray,
                                        is_airy=True)
        AbstractSpacecraftItem.__init__(self, position, angle,
                                    hull_shaqe, line_shaqe, battery_shaqe, cannon_shaqe,
                                    reactor_d1_shaqe, reactor_d2_shaqe,
                                    reactor_u_shaqe, reactor_l_shaqe, reactor_r_shaqe,
                                    cockpit_shaqe, text_shaqe,
                                    **kwargs)
        self.bullet_ready_time = time
        self.bomb_ready_time = time
        self.collision_function = self.collides

    def collides(self, arbiter, space, data):
        # (shape_a, shape_b) = arbiter.shapes
        # relative_speed = (shape_b.body.velocity-shape_a.body.velocity).length
        (body_a, body_b) = arbiter.bodies
        #relative_speed = (body_b.velocity-body_a.velocity).length
        contact_point = arbiter.contact_point_set.points[0]
        relative_speed = (body_b.velocity_at_world_point(contact_point.point_b)
                        - body_a.velocity_at_world_point(contact_point.point_a)).length
        Sound.hit1.play_once(volume=relative_speed ** 2 / 2e6)
        return True

    def thrust_up(self):
        Sound.thrust4.play_long()
        self.activate_thruster((0, -4.0e15), (-3, -11))
        self.activate_thruster((0, -4.0e15), (+3, -11))

    def thrust_down(self):
        Sound.thrust5.play_long()
        self.activate_thruster((0.0, +3e15), (0, +11))

    def thrust_left(self):
        Sound.thrust5.play_long()
        self.activate_thruster((-0.25e16, 0.0), (+19, 0))

    def thrust_right(self):
        Sound.thrust5.play_long()
        self.activate_thruster((+0.25e16, 0.0), (-19, 0))

    def fire(self):
        if uspace.time >= self.bullet_ready_time:
            #uspace.beep(440, 100)
            Sound.shoot2.play_once()
            self.bullet_ready_time = uspace.time + BULLET_REARM_DELAY_S
            (x, y) = self.position
            (vx, vy) = self.velocity
            a = self.angle
            (dx, dy) = (cos(a), sin(a))
            vx += BULLET_SPEED * dx
            vy += BULLET_SPEED * dy
            bullet = Bullet((x + 22 * dx - 4 * dy, y + 22 * dy + 4 * dx), a, (vx, vy),
                            delay_s=BULLET_LIFETIME_S)
            uspace.add_item(bullet)
            uspace.add_circle_item(bullet.position, 0.0,  # velocity=self.velocity,
                                   radius=2, brush=SpacecraftItem.fire_brush,
                                   body_type=munqy.KINEMATIC, is_airy=True,
                                   duration_s=0.15, with_fading=True)
            self.apply_impulse_at_local_point((-16e15, 0.0), (+16, 8))

    def drop_bomb(self):
        if uspace.time >= self.bomb_ready_time:
            Sound.say("Bomb dropped!")
            Sound.shoot2.play_once()
            #uspace.beep(120, 150)
            self.bomb_ready_time = uspace.time + BOMB_REARM_DELAY_S
            # winsound.PlaySound("shoot3.wav",winsound.SND_ASYNC)
            (x, y) = self.position
            a = self.angle
            (dx, dy) = (cos(a), sin(a))
            dv = (self.velocity.x - 100*dy , self.velocity.y + 100*dx)
            bomb = Bomb((x - 10 * dy, y + 10 * dx), a, dv, delay_s=BOMB_EXPLOSION_DELAY_S)
            uspace.add_item(bomb)


class SpacecraftItemP3(AbstractSpacecraftItem, munqy.CompoundItemDecomposable):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SpacecraftItemCSC(AbstractSpacecraftItem):

    def __init__(self, position, angle, **kwargs):
        hull_shaqe = munqy.RectShaqe(size=(16, 16), brush=QBrush(Qt.gray),
                                            density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        reactor_d1_shaqe = munqy.RectShaqe(size=(5, 4), offset=(-3, +7.5),
                                            brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                            density=1e12, elasticity=0.45, friction=0.2, **kwargs)
        reactor_d2_shaqe = munqy.RectShaqe(size=(5, 4), offset=(+3, +7.5),
                                            brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                            density=1e12, elasticity=0.45, friction=0.2, **kwargs)
        reactor_u_shaqe = munqy.RectShaqe(size=(4, 3), offset=(0, -7.5),
                                          brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                          density=1e12,elasticity=0.45, friction=0.9, **kwargs)
        reactor_l_shaqe = munqy.RectShaqe(size=(3, 4), offset=(-7.5, 0),
                                          brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                          density=1e12,elasticity=0.45, friction=0.9, **kwargs)
        reactor_r_shaqe = munqy.RectShaqe(size=(3,4), offset=(+7.5, 0),
                                          brush=QBrush(Qt.gray), pen=SpacecraftItem.shape_pen,
                                          density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        instrument_shaqe = munqy.CircleShaqe(5.0, (0.0, 0.0), brush=QBrush(QColor("powderblue")),
                                          pen=QPen(Qt.darkGray, 1),
                                          density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        text_shaqe = munqy.TextShaqe("CSC", font_size=3, offset=(-5, -6),
                                     brush=QBrush(Qt.darkBlue),
                                     is_airy=True)
        AbstractSpacecraftItem.__init__(self, position, angle,
                                                hull_shaqe,
                                                reactor_d1_shaqe, reactor_d2_shaqe,
                                                reactor_u_shaqe, reactor_l_shaqe, reactor_r_shaqe,
                                                instrument_shaqe, text_shaqe,
                                                **kwargs)

    def thrust_up(self):
        self.activate_thruster((0, -4.0e14), (-3, -11))
        self.activate_thruster((0, -4.0e14), (+3, -11))

    def thrust_down(self):
        self.activate_thruster((0.0, +3e14), (0, +11))

    def thrust_left(self):
        self.activate_thruster((-0.25e15, 0.0), (+12, 0))

    def thrust_right(self):
        self.activate_thruster((+0.25e15, 0.0), (-12, 0))


class SpacecraftItemOSC(AbstractSpacecraftItem):

    def __init__(self, position, angle, **kwargs):
        hull_shaqe = munqy.RectShaqe(size=(14, 14), brush=QBrush(Qt.gray),
                                            density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        occulter_shaqe = munqy.CircleShaqe(radius=8, pen=QPen(QColor(120, 120, 120)), brush=QBrush(QColor(100, 100, 100)),
                                            density=1e12, elasticity=0.45, friction=0.3, **kwargs)
        text_shaqe = munqy.TextShaqe("OSC", font_size=3, offset=(-2, -4),
                                     brush=QBrush(Qt.darkBlue),
                                     is_airy=True)
        AbstractSpacecraftItem.__init__(self, position, angle,
                                                hull_shaqe, occulter_shaqe,
                                                # reactor_d1_shaqe, reactor_d2_shaqe,
                                                # reactor_u_shaqe, reactor_l_shaqe, reactor_r_shaqe,
                                                text_shaqe,
                                                **kwargs)

    def thrust_up(self):
        self.activate_thruster((0, -4.0e15), (-3, -11))
        self.activate_thruster((0, -4.0e15), (+3, -11))

    def thrust_down(self):
        self.activate_thruster((0.0, +3e15), (0, +11))

    def thrust_left(self):
        self.activate_thruster((-0.25e16, 0.0), (+12, 0))

    def thrust_right(self):
        self.activate_thruster((+0.25e16, 0.0), (-12, 0))


class ParticleItem(munqy.CircleItem):

    def __init__(self, position, velocity, brush, **kwds):
        munqy.CircleItem.__init__(self, position, 0.0, velocity=velocity, radius=0.75, brush=brush, **kwds)


class Platform(munqy.SegmentItem):

    __slots__ = ("_ax", "_ay", "_t")

    def __init__(self,position,angle,size,ax=0.0,ay=0.0,):
        munqy.SegmentItem.__init__(self, position, angle, size=size,
                                   body_type=munqy.KINEMATIC,
                                   color=Qt.gray, density=4.0e10, elasticity=0.25, friction=0.5)
        self._ax = ax
        self._ay = ay
        self._t = 0.0
        self._dt = PI2 / 200

    def do_update_velocity(self):
        # TODO
        s = sin(self._t)
        #s = sin(uspace.time/uspace.dt_s*PI2 / 200)
        self._dt = PI2 / 200 * uspace.dt_s / munqy.TIMER_ELAPSE
        self._t = (self._t+self._dt) % PI2
        self.velocity = (self._ax*s,self._ay*s)


class Bullet(munqy.SegmentItem):

    def __init__(self,position,angle,velocity,delay_s):
        munqy.SegmentItem.__init__(self,position,angle,velocity=velocity,size=(4,2),
                                   color=Qt.yellow,density=4.0e10,elasticity=0.25,friction=0.5,
                                   duration_s=delay_s,with_fading=True)

class Bomb(munqy.SegmentItem):

    brush = QBrush(QColor(255, 155, 155))

    def __init__(self,position,angle,velocity,delay_s):
        munqy.SegmentItem.__init__(self,position,angle,velocity=velocity,size=(4,3),
                                   color=Qt.red,density=4.0e10,elasticity=0.25,friction=0.5,
                                   duration_s=delay_s)

    def do_finalize(self):
        #uspace.beep(200, 250)
        Sound.explosion2.play_once()
        #winsound.Beep(440,250)
        #winsound.PlaySound("explosion1.wav",winsound.SND_ASYNC)
        (x,y) = self.position
        (vx,vy) = self.velocity
        # TODO
        #space = self.qg_item.scene()
        uspace.add_circle_item(self.position,0.0,#velocity=self.velocity,
                       radius=30,brush=Bomb.brush,
                       body_type=munqy.KINEMATIC,is_airy=True,
                       duration_s=0.5,with_fading=True)
        for _ in range(50):
            a = uniform(0,2*pi)
            (dx,dy) = (cos(a),sin(a))            
            position = (x+2*dx,y+2*dy)
            v = uniform(0.5,1.5) * 1e3
            velocity = (vx+v*dx, vy+v*dy)
            uspace.add_item(ParticleItem(position,velocity,Bomb.brush,
                                         density=4.0e12,elasticity=0.65,friction=1,
                                         duration_s=0.3))

#QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
munqy.WIREFRAME_MODE = sys.argv[-1].startswith("w")
munqy.WIREFRAME_OPAQUE = sys.argv[-1].endswith("o") 
uspace = USpace()
uspace.show()
uspace.start()
