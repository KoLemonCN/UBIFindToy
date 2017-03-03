__author__ = 'Zongqi Wang'
from sensorshim import *
from grovepi import *
import time
import timeit
import grovelcd


class BotInput(object):
    """
    This class is designed to hold input from grove pi.
    Particularly
    1, the distance values from rangers.
    2, light values from light sensor
    3, button values from button
    4, vibration values from vibration to detect collisions.
    """
    def __init__(self):
        self.distance_front = 1000
        self.distance_up = 1000
        self.distance_down = 0
        self.distance_left = 1000
        self.distance_right = 1000
        self.light = 1000
        self.button = 0
        self.vibration = 0

    def set_distance_front(self, val):
        """
        The value to represent the distance from bot to front object.
        """
        self.distance_front = val

    def set_distance_left(self, val):
        """
        The value to represent the distance from bot to left object.
        """
        self.distance_left = val

    def set_distance_right(self, val):
        """
        The value to represent the distance from bot to right object.
        """
        self.distance_right = val

    def set_distance_up(self, val):
        """
        The value to represent the distance from bot to object above.
        """
        self.distance_up = val

    def set_distance_down(self, val):
        """
        The value to represent the distance from bot to object below.
        """
        self.distance_down = val

    def set_light(self, val):
        """
        The value to represent the light value.
        """
        self.light = val

    def set_vibration(self, val):
        """
        The value to represent the vibration value.
        """
        self.vibration = val

    def set_button(self, val):
        """
        The value to represent the button value.
        """
        self.button = val

    def __str__(self):
        s = "<UBIInput> "
        s += "[front {}\t".format(self.distance_front)
        s += "up {}\tdown {}\t".format(self.distance_up, self.distance_down)
        s += "left {}\tright {}\t".format(self.distance_left, self.distance_right)
        s += "[light {}]\t".format(self.light)
        s += "[button {}\t]".format(self.button)
        s += "[vibration {}\t]".format(self.vibration)
        return s

    def __repr__(self):
        return self.__str__()


class Bot(object):
    # maximum log the Bot will carry.
    LOG_LENGTH = 1000
    # the threshold for the bot to determine a collision.
    COLLISION = 1000
    # the with of the bot
    WIDTH = 30
    # the height of the bot
    HEIGHT = 10
    # the radius of the bot
    RADIUS = WIDTH / 2.0
    # the bot has 3 modes, auto, light and reset.
    # auto mode: the bot will perform automatic navigation.
    MODE_AUTO = "AUTO"
    # light mode: the bot will be guided with the help of light, then change to auto mode.
    MODE_LIGHT = "LIGHT"
    # reset mode: when time is out, the bot will try to go to initial place.
    MODE_RESET = "RESET"
    # the time limit for the bot being guided by light in seconds.
    TIME_LIGHT_LIMIT = 60
    # the time limit for the bot to perform automatic navigation in seconds.
    TIME_AUTO_LIMIT = 600
    # the light range for the bot to perform automatic navigation.
    LIGHT_RANGE = 50
    # the distance for the bot to slow down if the bot detects a near object.
    WARNING_DISTANCE = 10

    def __init__(self):
        self.log = []
        self.text = ""
        self.mode = Bot.MODE_AUTO
        self.time = timeit.timeit()
        self.low_light = 1000

    def process_input(self, bot_input):
        """
        The only open method for the bot to process the input from grove pi.
        the process could be generally described as:
        1, keep log of the current values
        2, the bot will update the mode
            a, if the button is pressed
            b, if the time for the current mode runs out.
        3, detects if the bot is going to fall
            a, if yes, the bot will turn back, and find a new direction to try.
        4, detects if the bot is colliding with other objects
            a, if yes, the bot will turn back, and find a new direction to try.
        5, detects if the bot can pass through the path and move forward.
            a, if no, the bot will turn back, and find a new direction to try.
        6, detects if the bot is about to hit objects in front
            a, if yes, the bot will slow down the speed.
        7, apply actions according to current mode and input.
        """
        self.__update_log(bot_input)
        if len(self.log) < 2:
            self.low_light = bot_input.light
            return

        # the next line is used for debugging.
        print "<Bot process_input>", self.log[-1]

        self.__update_mode(bot_input)

        if self.__test_fall(bot_input):
            self.__handle_fall()
            return
        elif self.__test_collision(bot_input):
            self.__handle_collision()
            return
        elif not self.__test_go_through(bot_input):
            self.__handle_not_go_through()
            return

        self.__apply_collision_protection(bot_input)

        if self.mode == Bot.MODE_AUTO:
            self.__apply_auto_mode()
        elif self.mode == Bot.MODE_LIGHT:
            self.__apply_light_mode()
        elif self.mode == Bot.MODE_RESET:
            self.__apply_reset_mode()

    def __set_display_lcd(self, text):
        self.text = text
        grovelcd.setText(text)

    def __add_display_lcd(self, text):
        self.text += text
        grovelcd.setText(text)

    def __apply_collision_protection(self, bot_input):
        """
        If the bot detects near objects, slow down the speed to protect the bot.
        """
        distance_front = bot_input.distance_front
        if distance_front <= Bot.WARNING_DISTANCE:
            print "please move slowly. the bot is about to hit objects."
            self.__set_display_lcd("please move slowly. the bot is about to hit objects.")

    def __update_mode(self, bot_input):
        """
        This method handles mode changes.
        1, test the time, if longer than time limit, switch to other modes accordingly.
        2, if the button is pressed, reset the time, and switch to other modes accordingly.
        """
        # calculate passed time
        passed_time = timeit.timeit() - self.time
        # test if the time is out of limit
        if self.mode == Bot.MODE_LIGHT and passed_time >= Bot.TIME_LIGHT_LIMIT:
            # change mode and reset values.
            self.mode = Bot.MODE_AUTO
            self.low_light = self.log[-1].light
            print "<time out> Bot mode changed to", self.mode
            self.__set_display_lcd("<time out> Bot mode changed to " + self.mode)
            return
        elif self.mode == Bot.MODE_AUTO and passed_time >= Bot.TIME_AUTO_LIMIT:
            # change mode and reset values.
            self.mode = Bot.MODE_RESET
            print "<time out> Bot mode changed to", self.mode
            self.__set_display_lcd("<time out> Bot mode changed to " + self.mode)
            return

        # test if the button is pressed
        if bot_input.button and not self.log[-2].button:
            # update the time
            self.time = timeit.timeit()
            # change mode according to current mode.
            if self.mode == Bot.MODE_AUTO:
                self.mode = Bot.MODE_LIGHT
                self.low_light = self.log[-1].light
            else:
                self.mode = Bot.MODE_AUTO
                self.low_light = self.log[-1].light
            print "Bot mode changed to", self.mode
            self.__set_display_lcd("Bot mode changed to " + self.mode)

    def __apply_auto_mode(self):
        """
        The auto mode defines the behaviour of the bot
        normally, the bot would move forward.
        meanwhile, the light value would also be monitored.
        """
        print "Bot mode <{}>".format(self.mode)
        low = self.low_light - Bot.LIGHT_RANGE
        current = self.log[-1].light
        high = self.low_light + Bot.LIGHT_RANGE
        if low <= current <= high:
            print "Action: move forward."
            self.__set_display_lcd("Action: move forward.")
        else:
            print "WARNING: light value out of range. Move Back!"
            self.__set_display_lcd("WARNING: light value out of range. Move Back!")
            print "light range [{} - {}], current {}".format(low, high, current)
            self.__add_display_lcd("light range [{} - {}], current {}".format(low, high, current))

    def __apply_light_mode(self):
        """
        The light mode defines the behaviour of the bot.
        the bot would try to find the place with lower light value until the mode turns off.
        """
        print "Bot mode <{}>".format(self.mode), "Action: move to find place with lower light value."
        self.__set_display_lcd("Bot mode <{}>".format(self.mode) + "Action: move to find place with lower light value.")
        if self.log[-1].light < self.low_light:
            self.low_light = self.log[-1].light

        print "current light value:", self.log[-1].light, "low light value: ", self.low_light
        self.__add_display_lcd("current light value:{} low light value: {}".format(self.log[-1].light, self.low_light))

    def __apply_reset_mode(self):
        """
        The bot would return to initial place in reset mode.
        this mode is designed to handle exceptions.
        """
        print "Bot mode <{}>".format(self.mode), "Action: move to initial place."
        self.__set_display_lcd("Bot mode <{}>".format(self.mode) + "Action: move to initial place.")


    def __update_log(self, bot_input):
        """
        the bot would record the input from grove pi.
        in this case, the maximum length is defined to avoid wasting memory resources.
        """
        if len(self.log) >= Bot.LOG_LENGTH:
            self.log.pop(0)
        self.log.append(bot_input)

    def __test_go_through(self, bot_input):
        """
        test if the bot can pass through the path
        """
        return bot_input.distance_left > Bot.RADIUS and bot_input.distance_right > Bot.RADIUS

    def __test_fall(self, bot_input):
        """
        test if the bot would fall if continue moving forward.
        """
        return bot_input.distance_down > Bot.HEIGHT/2

    def __test_collision(self, bot_input):
        """
        test if the bot is colliding with objects.
        """
        return bot_input.vibration > Bot.COLLISION

    def __handle_fall(self):
        """
        the behaviour if a potential fall is detected.
        """
        print "The bot is going to fall, move back."
        self.__set_display_lcd("The bot is going to fall, move back.")

    def __handle_collision(self):
        """
        the behaviour if collisions are detected.
        """
        print "The bot collides with other objects, turn back and select new direction."
        self.__set_display_lcd("The bot collides with other objects, turn back and select new direction.")

    def __handle_not_go_through(self):
        """
        the behaviour if the bot cannot pass the current path.
        """
        print "The bot cannot go through the current path, turn back and select new direction."
        self.__set_display_lcd("The bot cannot go through the current path, turn back and select new direction.")

# initialize the sensors
sensors = {
    "button": (SensorShim.DIGITAL, 8),
    "light": (SensorShim.ANALOG, 0),
    "vibration": (SensorShim.ANALOG, 1)
}
sensorObj = SensorShim(sensors)

def get_bot_input():
    """
    Get all necessary information from the grove pi sensors.
    """
    bot_input = BotInput()
    bot_input.distance_front = ultrasonicRead(2)
    #bot_input.distance_up = ultrasonicRead(3)
    #bot_input.distance_down = ultrasonicRead(4)
    #bot_input.distance_left = ultrasonicRead(5)
    #bot_input.distance_right = ultrasonicRead(6)
    bot_input.button = sensorObj.getValue("button")
    bot_input.light = sensorObj.getValue("light")
    bot_input.vibration = sensorObj.getValue("vibration")
    return bot_input

def main():
    bot = Bot()
    frequency = 5
    time_gap = 1.0 / frequency
    while True:
        # get all necessary data from grove pi and pass the information to bot for processing
        bot.process_input(get_bot_input())
        time.sleep(time_gap)

if __name__ == "__main__":
    main()
