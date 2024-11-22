import os
import pygame

from threading import Thread
from kivy.animation import Animation
os.environ['DISPLAY'] = ":0.0"
# os.environ['KIVY_WINDOW'] = 'egl_rpi'
from time import sleep
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from numpy.version import release
from pidev.MixPanel import MixPanel
from pidev.kivy.PassCodeScreen import PassCodeScreen
from pidev.kivy.PauseScreen import PauseScreen
from pidev.kivy import DPEAButton
from pidev.kivy import ImageButton
from pidev.kivy.selfupdatinglabel import SelfUpdatingLabel
from kivy.uix.behaviors import ButtonBehavior
from pidev.Joystick import Joystick
from kivy.clock import Clock

from kivy.config import Config

from kivy.uix.image import Image

from datetime import datetime

time = datetime

MIXPANEL_TOKEN = "x"
MIXPANEL = MixPanel("Project Name", MIXPANEL_TOKEN)

SCREEN_MANAGER = ScreenManager()
MAIN_SCREEN_NAME = 'main'
ADMIN_SCREEN_NAME = 'admin'
JOYSTICK_SCREEN_NAME = 'joystick'
THIRD_SCREEN_NAME = 'third'

###### code from DPi_Stepper_Startup
from dpeaDPi.DPiComputer import DPiComputer
from dpeaDPi.DPiStepper import *
from time import sleep



try:
    joy = Joystick(0, False)
except pygame.error as e:
    print("No joystick connected, please connect and try again.")
    exit(1)

##### Motor Setup:

# Stepper:
dpiStepper = DPiStepper()
dpiStepper.setBoardNumber(0)
if not dpiStepper.initialize():
    print("Communication with the DPiStepper board failed.")

# Servo:
dpiComputer = DPiComputer()
dpiComputer.initialize()

#####

class MotorButtonsGUI(App):
    """
    Class to handle running the GUI Application
    """

    def build(self):
        """
        Build the application
        :return: Kivy Screen Manager instance
        """
        return SCREEN_MANAGER

Window.clearcolor = (1, 1, 1, 1)  # White

class MainScreen(Screen):
    """
    Class to handle the main screen and its associated touch events
    """
    red = (1.0, 0.0, 0.0, 1.0)
    green = (0.0, 1.0, 0.0, 1.0)
    btn_x = 100
    btn_y = 100
    pressed_var = False
    motor_scheduled = False
    percent_100_speed = 10 # revolutions per second

    def __init__(self, **kwargs):
        super(Screen, self).__init__(**kwargs)

    servo_scheduled = False
    def schedule_servo_motor(self):
        if not self.servo_scheduled:
            self.servo_scheduled = True
            Clock.schedule_interval(self.check_switch_for_servo_motor, 0.05)
            self.ids.servo_motor_script_button_text.text = "Servo\nSche-\nduled"
        else:
            self.servo_scheduled = False
            Clock.unschedule(self.check_switch_for_servo_motor)
            Clock.schedule_once(self.reset_servo_label, 3)
            self.ids.servo_motor_script_button_text.text = "Servo\nUnsch-\neduled"

    def reset_servo_label(self, dt=0):
        self.ids.servo_motor_script_button_text.text = "Servo\nMotor"

    def check_switch_for_servo_motor(self, dt=0):
        servo_num = 0
        if dpiComputer.readDigitalIn(dpiComputer.IN_CONNECTOR__IN_0) == 0:
            dpiComputer.writeServo(servo_num, 180)
        else:
            dpiComputer.writeServo(servo_num, 0)

    def spin_motor(self, dt = None):
        # Some default values
        microstepping = 8
        # allows the motor to spin continuously
        wait_to_finish_moving_flg = False
        # the stepper that you would like to control
        stepper_num = 0
        # steps control how smooth the motor spins
        steps = 320000
        # gets a value (-100 to 100) from a slider named "position"
        slider_value = self.ids.position.value
        # checks if the slider is zero or if the button controlling to motor is off
        #print(True)
        if not self.motor_on or slider_value == 0:
            dpiStepper.decelerateToAStop(0)
            dpiStepper.enableMotors(False)
            return
        # if motor was disabled from being at zero or off, enable the motor
        elif not dpiStepper.getStepperStatus(stepper_num)[2]:
            dpiStepper.enableMotors(True)
        self.set_motor_speed_by_revs_per_sec((abs(slider_value) / self.percent_100_speed), stepper_num)
        if slider_value < 0:
            steps = -steps
        dpiStepper.moveToRelativePositionInSteps(stepper_num, steps, wait_to_finish_moving_flg)

    motor_on = False
    def schedule_motor(self, motor_on):
        self.motor_on = motor_on
        if not self.motor_scheduled and self.motor_on:
            self.motor_scheduled = True
            Clock.schedule_interval(self.spin_motor, .001)
        elif self.motor_scheduled and not self.motor_on:
            self.motor_scheduled = False
            dpiStepper.decelerateToAStop(0)
            dpiStepper.enableMotors(self.motor_scheduled)
            Clock.unschedule(self.spin_motor)

    def run_motor_script(self):
        # create new thread so that kivy can update the label in real time
        t = Thread(target=self.motor_script)
        t.start()

    def motor_script(self):
        # disable the button
        self.ids.power_button.disabled = True
        self.ids.change_button.disabled = True
        self.ids.motor_script_button.disabled = True

        #  show that motor is on, but disable the button and slider until done with the program
        wait_to_finish_moving_flg = True
        # the stepper that you would like to control
        stepper_num = 0
        # steps control how smooth the motor spins
        one_rev_of_steps = 1600

        # displays step count
        self.display_curr_step_count(stepper_num)
        # goes home
        self.return_motor_to_home(stepper_num, wait_to_finish_moving_flg)
        # displays step count
        self.display_curr_step_count(stepper_num)
        # moves motor 15 cw rotations at 1 rotation per second
        self.set_motor_speed_by_revs_per_sec(1, stepper_num)
        dpiStepper.enableMotors(True)
        steps = one_rev_of_steps * 15
        dpiStepper.moveToRelativePositionInSteps(stepper_num, steps, wait_to_finish_moving_flg)
        dpiStepper.enableMotors(False)
        # displays step count
        self.display_curr_step_count(stepper_num)

        # moves motor 10 cw rotations at 5 rotations per seconds
        self.set_motor_speed_by_revs_per_sec(5, stepper_num)
        dpiStepper.enableMotors(True)
        steps = one_rev_of_steps * 10
        dpiStepper.moveToRelativePositionInSteps(stepper_num, steps, wait_to_finish_moving_flg)
        dpiStepper.enableMotors(False)
        # displays step count
        self.display_curr_step_count(stepper_num)

        # wait 5 second
        sleep(5)
        # goes home
        self.return_motor_to_home(stepper_num, wait_to_finish_moving_flg)
        # displays step count
        self.display_curr_step_count(stepper_num)

        # turns counterclockwise for 100 revolutions at 8 revs per sec
        self.set_motor_speed_by_revs_per_sec(8, stepper_num)
        dpiStepper.enableMotors(True)
        steps = one_rev_of_steps * -100
        dpiStepper.moveToRelativePositionInSteps(stepper_num, steps, wait_to_finish_moving_flg)
        dpiStepper.enableMotors(False)
        # displays step count
        self.display_curr_step_count(stepper_num)

        # waits for 5 seconds
        sleep(5)
        # goes home
        self.return_motor_to_home(stepper_num, wait_to_finish_moving_flg)
        # displays step count
        self.display_curr_step_count(stepper_num)

        # set button label to normal and re-enable the button
        Clock.schedule_once(self.set_motor_script_display_normal, 3)
        self.ids.motor_script_button.disabled = False
        self.ids.power_button.disabled = False
        self.ids.change_button.disabled = False

    def return_motor_to_home(self, stepper_num = 0, wait_to_finish_moving_flg = True):
        self.set_motor_speed_by_revs_per_sec(10, stepper_num)
        dpiStepper.enableMotors(True)
        steps = -dpiStepper.getCurrentPositionInSteps(stepper_num)[1]
        dpiStepper.moveToRelativePositionInSteps(stepper_num, steps, wait_to_finish_moving_flg)
        dpiStepper.enableMotors(False)

    def set_motor_speed_by_revs_per_sec(self, revs_per_sec, stepper_num):
        microstepping = 8
        speed_steps_per_second = (200 * microstepping) * revs_per_sec
        accel_steps_per_second_per_second = speed_steps_per_second
        dpiStepper.setSpeedInStepsPerSecond(stepper_num, speed_steps_per_second)
        dpiStepper.setAccelerationInStepsPerSecondPerSecond(stepper_num, accel_steps_per_second_per_second)

    def display_curr_step_count(self, stepper_num=0):
        curr_steps = dpiStepper.getCurrentPositionInSteps(int(stepper_num))[1]
        if curr_steps > 1000000:
            curr_steps = str(round(curr_steps / 1000000, 2)) + "M"
        if curr_steps < -1000000:
            curr_steps = str(int(round(curr_steps / 1000000, 0))) + "M"
        elif curr_steps < -100000:
            curr_steps = str(int(round(curr_steps / 1000, 0))) + "K"
        self.ids.motor_script_button_text.text = "Current\nSteps:\n" + str(curr_steps)

    def set_motor_script_display_normal(self, dt=0):
        self.ids.motor_script_button_text.text = "Stepper\nScript"

    def counter_pressed(self):
        self.ids["counter_button_text"].text = str(int(self.ids["counter_button_text"].text) + 1)

    def motor_pressed(self, dt=0):
        self.pressed_var = not self.pressed_var
        if self.pressed_var:
            self.ids['power_button'].color = self.green
            self.ids['power_button_text'].text = "Stepper\nOn"
            self.ids.motor_script_button.disabled = True
            self.schedule_motor(True)
        else:
            self.ids['power_button'].color = self.red
            self.ids['power_button_text'].text = "Stepper\nOff"
            self.schedule_motor(False)
            self.ids.motor_script_button.disabled = False
        if self.ids['power_button'].mouseover_color:
            self.ids['power_button'].original_color = self.ids['power_button'].color
            self.ids['power_button'].color = self.ids['power_button'].multiply_colors(self.ids['power_button'].hover_color, self.ids['power_button'].color)

    def switch_screen(self):
        SCREEN_MANAGER.current = JOYSTICK_SCREEN_NAME

    def admin_action(self):
        """
        Hidden admin button touch event. Transitions to passCodeScreen.
        This method is called from pidev/kivy/PassCodeScreen.kv
        :return: None
        """
        SCREEN_MANAGER.current = 'passCode'

    def on_load(self):
        print("load")

class JoystickScreen(Screen):
    btn_x = 100
    btn_y = 100
    target_icon_id = "target_icon_btn"

    def __init__(self, **kwargs):
        # this line useful if we want to add attributes but still keep all Screen attributes
        super(JoystickScreen, self).__init__(**kwargs)
        self.joystick_scheduled = False
        # you can make x and y values be instance attributes like this, so they are accessible anywhere in the program
        self.x_val = 0
        self.y_val = 0
        self.schedule_joy_update()

    def counter_pressed(self):
        self.ids["counter_button_text"].text = str(int(self.ids["counter_button_text"].text) + 1)

    def move_icon(self):
        current_x_movement, current_y_movement = joy.get_both_axes()
        sensitivity = (1 / 50)
        # the x/y amount to add to the position
        x_add = self.x_val * Window.size[0] * sensitivity
        y_add = -self.y_val * Window.size[1] * sensitivity
        # rounds to avoid floating point issues
        current_x_movement = round(current_x_movement, 3)
        current_y_movement = round(current_y_movement, 3)
        # arbitrary number, whatever works best
        range_of_drift = 0.1
        # prevents drift
        # if its is within range_of_drift amount of variation, and that variation is within a small amount of what that last checked variation was
        if (-range_of_drift < current_x_movement < range_of_drift) and (-range_of_drift < current_y_movement < range_of_drift):
            return
        # for testing if the new coords would be beyond the border of the screen
        new_x = self.ids[self.target_icon_id].center_x + x_add
        new_y = self.ids[self.target_icon_id].center_y + y_add
        self.ids[self.target_icon_id].center_x += x_add if 0 < new_x < Window.size[0] else 0
        self.ids[self.target_icon_id].center_y += y_add if 0 < new_y < Window.size[1] else 0
        # check if over button to have button register anim
        curr_x = self.ids[self.target_icon_id].center_x
        curr_y = self.ids[self.target_icon_id].center_y
        for child in SCREEN_MANAGER.current_screen.children:
            if child == self.ids[self.target_icon_id]:
                continue
            try:
                if child.type == "BetterImageButton":

                    BetterImageButton.on_mouseover(child, None, (curr_x, curr_y))

            except:
                continue

    def joy_update(self, dt=None):
        # dt for clock scheduling
        self.check_buttons_clicked()
        if SCREEN_MANAGER.current == JOYSTICK_SCREEN_NAME:  # Only update if active screen is joystick screen
            self.x_val, self.y_val = joy.get_both_axes()
            # updates labels to reflect the current x/y movement of the joystick
            self.ids.x.text = "X: " + str(round(self.x_val, 3))
            self.ids.y.text = "Y: " + str(round(self.y_val, 3))
            self.move_icon()

    button_0 = False
    def check_buttons_clicked(self):
        self.buttons_pressed = ""
        for num in range(10):
            if joy.get_button_state(num):
                if self.buttons_pressed != "":
                    self.buttons_pressed += "\n"
                self.buttons_pressed += "Button " + str(1 + num) + " Pressed"
        if self.buttons_pressed == "":
            self.buttons_pressed = "No Buttons Pressed"
        self.ids["buttons_pressed_text"].text = self.buttons_pressed

        if not self.button_0 and joy.get_button_state(0):
            self.button_0 = True
            for child in SCREEN_MANAGER.current_screen.children:
                if child == self.ids[self.target_icon_id]:
                    continue
                try:
                    if child.type == "BetterImageButton":
                        curr_x = self.ids[self.target_icon_id].center_x
                        curr_y = self.ids[self.target_icon_id].center_y
                        between_x, between_y = child.x <= curr_x <= (child.x + child.size[0]), child.y <= curr_y <= (child.y + child.size[1])
                        if between_x and between_y:
                            child.trigger_action()

                except:
                    continue
            pass
        elif self.button_0 and not joy.get_button_state(0):
            self.button_0 = False
        else:
            return


    def schedule_joy_update(self):
        if not self.joystick_scheduled:  # only schedule once
            Clock.schedule_interval(self.joy_update, .01) # schedules joy_update to run every .1 seconds
            #Clock.schedule_interval(self.check_button_0_clicked, .01)
            self.joystick_scheduled = True
        else:
            self.joystick_scheduled = False  # joy_update will now return false and thus unschedule the Clock event

    @staticmethod
    def switch_screen_third():
        SCREEN_MANAGER.transition.direction = "up"
        SCREEN_MANAGER.current = THIRD_SCREEN_NAME

    def switch_screen_main(self):
        SCREEN_MANAGER.current = MAIN_SCREEN_NAME

class ThirdScreen(Screen):
    btn_x = 100
    btn_y = 100

    def switch_screen_main(self):
        SCREEN_MANAGER.current = MAIN_SCREEN_NAME

    def switch_screen_joystick(self):
        SCREEN_MANAGER.transition.direction = "down"
        SCREEN_MANAGER.current = JOYSTICK_SCREEN_NAME

class BetterImageButton(ButtonBehavior, Image):
    current_button_id = 0 # static variable to keep track of all buttons
    button_id = 0 # the individual button id
    type = "BetterImageButton"
    def __init__(self, **kwargs):
        """
        Constructor for the better image button
        When using specify : id, source, size, position, on_press, on_release
        :param kwargs: Arguments supplied to super
        """
        super(BetterImageButton, self).__init__(**kwargs)
        Window.bind(mouse_pos=self.on_mouseover)
        self.size_hint = None, None
        self.keep_ratio = False
        self.allow_stretch = True
        self.size = 150, 150
        self.background_color = 0, 0, 0, 0
        self.background_normal = ''
        # handles the button_id, each button will have a unique number
        self.button_id = BetterImageButton.current_button_id
        BetterImageButton.current_button_id += 1
        # set the source here for all buttons to have the same image or in you .kv file for a button by button basis
        self.source = "WhiteButtonWithBlackBorder.png"

    # appends the button_id to the end of what self returns to allow for a complete individual reference to each button (the base self return is based off of position, meaning that two buttons could be mixed up)
    def __repr__(self):
        return super(BetterImageButton, self).__repr__() + str(self.button_id)

    # multiplies the two colors together by their individual rgba values
    def multiply_colors(self, color1, color2):
        return (color1[0] * color2[0], color1[1] * color2[1], color1[2] * color2[2], color1[3] * color2[3])


    # the (mouseover_color) or (mouseover_size) at the end shows which mouseover methods use them
    # if there is none, they both use them
    # any (mouseover_color) variable is also use by (mouseover_size) if both are True

    # determines what color to change the button to when hovered over (mouseover_color)
    hover_color = (0.875, 0.875, 0.875, 1.0)
    # SHOULD be set. if not set, the mouseover_size_method will default it to 13/12 the size of the button (mouseover_size)
    hover_size = None
    # determines how long the hover size animation will run (in seconds) (mouseover_size)
    hover_size_anim_duration = 0.125
    # Shouldn't be set, the mouseover methods will handle it (mouseover_color)
    original_color = (0.0, 0.0, 0.0, 0.0)
    # original_size and original_pos shouldn't need to be set because the mouseover_size_method will handle them (mouseover_size)
    # needs to be a large negative number to avoid a None type error (if I used None) or other potential design issues using another, closer to zero number
    original_size = original_pos = [-2147483647, -2147483647]
    # already_hovered is for either method, and handles the one time variable setting
    already_hovered = False
    # on_hover tells whether the button is currently being hovered over or not
    on_hover = False
    # controls whether the color is multiplied, or just set (mouseover_color)
    mouseover_multiply_colors = True
    # can be set to false to remove mouseover capabilities
    mouseover = True
    # determines which mouseover methods should run, one or both can be enabled
    mouseover_color = False
    mouseover_size = False
    # for handling new screens
    current_screen = ""
    previous_screen = ""

    # runs on everytime mouse is with in the window
    def on_mouseover(self, window, pos):
        if self.mouseover:
            # if both mouseover_color and mouseover_size are true, the mouseover_size_method handles that
            # if not, mouseover_size_method still works for just mouseover_size
            # mouseover_color_method works for just mouseover_color
            if self.mouseover_size:
                self.mouseover_size_method(window, pos)
            elif self.mouseover_color:
                self.mouseover_color_method(window, pos)

    def mouseover_color_method(self, window, pos):
        if not self.already_hovered:
            self.already_hovered = True
            self.original_color = self.color
        # runs when the button is being hovered over
        # it runs once, as soon as the cursor is OVER the button
        if not self.on_hover and self.collide_point(*pos):
            self.on_hover = True
            # multiplies the color (or just sets the color) to hover_color
            if self.mouseover_multiply_colors:
                self.color = self.multiply_colors(self.hover_color, self.color)
            else:
                self.color = self.hover_color
        # runs when not hovering over the button
        # it runs once, as soon as the cursor is OFF the button
        elif not self.collide_point(*pos) and self.on_hover:
            self.on_hover = False
            self.color = self.original_color

    def mouseover_size_method(self, widow, pos):
        # runs once per each button, even ones in other screens (than the one fist pulled up)
        # sets values for original_size, hover_size (if one wasn't set), and original_color
        if not self.already_hovered:
            self.already_hovered = True
            self.original_size = [self.size[0], self.size[1]]
            if not self.hover_size:
                self.hover_size = [self.size[0] * (13/12), self.size[1] * (13/12)]
            # for color handling
            # checks if the color should change too, and sets a default value if so
            if self.mouseover_color:
                self.original_color = self.color
        # runs each time a different screen is entered
        if self.current_screen != SCREEN_MANAGER.current:
            self.previous_screen = self.current_screen
            self.current_screen = SCREEN_MANAGER.current
            # ensures that when switching screens, the original_pos does not get set wrongly due to its animation
            # the == [-2147483647, -2147483647] check ensures that the original position is only set once
            # this can't be in the "run once only" if statement because it is on a screen not currently loaded, it will default to [0,0], not its actual position
            if self.original_pos == [-2147483647, -2147483647] and self in SCREEN_MANAGER.current_screen.children: # looking at the new screens children, to see if the new button is in it
                self.original_pos = [self.x, self.y]
        # runs when the button is being hovered over
        # it runs once (because of on_hover), as soon as the cursor is OVER the button
        if not self.on_hover and self.collide_point(*pos):
            self.on_hover = True
            # for color handling
            # checks if the color should change too, and multiplies the color (or just sets the color) to hover_color
            if self.mouseover_color:
                if self.mouseover_multiply_colors:
                    self.color = self.multiply_colors(self.hover_color, self.color)
                else:
                    self.color = self.hover_color
            # animates the button to be the size of hover_size over the course of hover_size_anim_duration
            # the x/y part of the animation keeps the button centered on its original position (necessary because kivy size animations expand from the bottom left out)
            # I use the x/y values here and not center_x/y values, because when I did, the animation was too jittery
            on_hover_anim = Animation(x=(self.x + self.original_size[0]/2) - self.hover_size[0]/2, y=(self.y + self.original_size[1]/2) - self.hover_size[1]/2, size=(self.hover_size[0], self.hover_size[1]), duration=self.hover_size_anim_duration)
            on_hover_anim.start(self)
        # runs when not hovering over the button
        # it runs once (because of on_hover), as soon as the cursor is OFF the button
        elif not self.collide_point(*pos) and self.on_hover:
            self.on_hover = False
            # animates the button back to its original size, while keeping the position centered
            off_hover_anim = Animation(x=self.original_pos[0], y=self.original_pos[1], size=(self.original_size[0], self.original_size[1]), duration=self.hover_size_anim_duration)
            off_hover_anim.start(self)
            # for color handling
            # checks if the color should be changing too, and sets it back to the original color if so
            if self.mouseover_color:
                self.color = self.original_color

class AdminScreen(Screen):
    """
    Class to handle the AdminScreen and its functionality
    """

    def __init__(self, **kwargs):
        """
        Load the AdminScreen.kv file. Set the necessary names of the screens for the PassCodeScreen to transition to.
        Lastly super Screen's __init__
        :param kwargs: Normal kivy.uix.screenmanager.Screen attributes
        """
        Builder.load_file('AdminScreen.kv')

        PassCodeScreen.set_admin_events_screen(ADMIN_SCREEN_NAME)  # Specify screen name to transition to after correct password
        PassCodeScreen.set_transition_back_screen(MAIN_SCREEN_NAME)  # set screen name to transition to if "Back to Game is pressed"

        super(AdminScreen, self).__init__(**kwargs)

    @staticmethod
    def transition_back():
        """
        Transition back to the main screen
        :return:
        """
        SCREEN_MANAGER.current = MAIN_SCREEN_NAME

    @staticmethod
    def shutdown():
        """
        Shutdown the system. This should free all steppers and do any cleanup necessary
        :return: None
        """
        os.system("sudo shutdown now")

    @staticmethod
    def exit_program():
        """
        Quit the program. This should free all steppers and do any cleanup necessary
        :return: None
        """
        quit()


"""
Widget additions
"""

Builder.load_file('main.kv')
Builder.load_file('joystick.kv')
Builder.load_file('third.kv')
SCREEN_MANAGER.add_widget(MainScreen(name=MAIN_SCREEN_NAME))
SCREEN_MANAGER.add_widget(JoystickScreen(name=JOYSTICK_SCREEN_NAME))
SCREEN_MANAGER.add_widget(ThirdScreen(name=THIRD_SCREEN_NAME))

SCREEN_MANAGER.add_widget(PassCodeScreen(name='passCode'))
SCREEN_MANAGER.add_widget(PauseScreen(name='pauseScene'))
SCREEN_MANAGER.add_widget(AdminScreen(name=ADMIN_SCREEN_NAME))

"""
MixPanel
"""


def send_event(event_name):
    """
    Send an event to MixPanel without properties
    :param event_name: Name of the event
    :return: None
    """
    global MIXPANEL

    MIXPANEL.set_event_name(event_name)
    MIXPANEL.send_event()


if __name__ == "__main__":
    # send_event("Project Initialized")
    Config.set('graphics', 'fullscreen', 'auto')
    Config.set('graphics', 'window_state', 'maximized')
    Config.write()

    MotorButtonsGUI().run()

