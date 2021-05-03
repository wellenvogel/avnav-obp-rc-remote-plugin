'''
remote control from https://www.segeln-forum.de/user/19350-chrhartz/
for a raspberry pi
plugin for AvNav
'''

import time
hasPackages=True
try:
  import smbus
  import RPi.GPIO as gpio
except:
  hasPackages=False

# ir-receiver I2C address
address = 0x14


# keycodes
PB_ZOOM_OUT = 0x00
PB_ZOOM_IN = 0x01
PB_CSR_UP = 0x02
PB_CSR_UP_RPT = 0x42
PB_CSR_LT = 0x03
PB_CSR_LT_RPT = 0x43
PB_CSR_RT = 0x04
PB_CSR_RT_RPT = 0x44
PB_CSR_DN = 0x05
PB_CSR_DN_RPT = 0x45
PB_MOUSE_LT = 0x06
PB_MOUSE_RT = 0x07
PB_ESC = 0x08
PB_RETURN = 0x09
PB_CENTER = 0x0a
PB_MOUSE_KB = 0x0b
PB_DASHBRD = 0x0c
PB_TAB = 0x0d

keyMap={
  PB_ZOOM_OUT: 'PageUp',
  PB_ZOOM_IN: 'PageDown',
  PB_RETURN: 'Enter',
  PB_CENTER: 'c',
  PB_ESC: 'Escape',
  PB_TAB: 'Tab',
  PB_CSR_RT: 'ArrowRight',
  PB_CSR_RT_RPT: 'ArrowRight',
  PB_CSR_UP: 'ArrowUp',
  PB_CSR_UP_RPT: 'ArrowUp',
  PB_CSR_DN: 'ArrowDown',
  PB_CSR_DN_RPT: 'ArrowDown'
}

class Plugin(object):
  CONFIG=[
    {
      'name':'irgPin',
      'default': 11,
      'type': 'NUMBER',
      'description': 'the irq pin in board numbering (the default of 11 is GPIO17)'
    }
  ]
  @classmethod
  def pluginInfo(cls):
    """
    the description for the module
    @return: a dict with the content described below
            parts:
               * description (mandatory)
               * data: list of keys to be stored (optional)
                 * path - the key - see AVNApi.addData, all pathes starting with "gps." will be sent to the GUI
                 * description
    """
    return {
      'description': 'plugin for chrhartz remote plugin'
    }

  def __init__(self,api):
    """
        initialize a plugins
        do any checks here and throw an exception on error
        do not yet start any threads!
        @param api: the api to communicate with avnav
        @type  api: AVNApi
    """
    self.api = api
    self.api.registerEditableParameters(self.CONFIG,self.updateParam)
    self.api.registerRestart(self.stop)
    self.configSequence=0

  def updateParam(self):
    pass
  def stop(self):
    pass

  def run(self):
    """
    the run method
    this will be called after successfully instantiating an instance
    this method will be called in a separate Thread
    The example simply counts the number of NMEA records that are flowing through avnav
    and writes them to the store every 10 records
    @return:
    """
    seq=0
    if not hasPackages:
      raise Exception("missing packages for remote control")
    self.api.setStatus('NMEA','running')
    i2c = smbus.SMBus(1)
    currentMode=gpio.getmode()
    if currentMode is None:
      gpio.setmode(gpio.BOARD)
    self.api.log("gpio mode=%d",gpio.getmode())
    lastIrq=None
    while not self.api.shouldStopMainThread():
      irq=int(self.api.getConfigValue('irgPin',11))
      if irq != lastIrq:
        self.api.log("using irq pin %d",irq)
        gpio.setup(irq, gpio.IN)
        lastIrq=irq
      try:
        c=gpio.wait_for_edge(irq, gpio.RISING,timeout=1000)
        if c is None:
          continue
        keycode = i2c.read_byte(address)
        v=keyMap.get(keycode)
        self.api.log("keycode=%d, translated=%s",keycode,v)
        if v is not None:
          self.api.sendRemoteCommand('K',v)
      except Exception as e:
        self.api.error("error: "%e)
        
    gpio.cleanup()


