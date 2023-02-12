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

# keycodes
keyNames={
  0x00:"ZOOM_OUT",
  0x01:"ZOOM_IN",
  0x02:"UP",
  0x03:"LEFT",
  0x04:"RIGHT",
  0x05:"DOWN",
  0x06:"LOCK",
  0x07:"DASHBOARD",
  0x08:"STOP",
  0x09:"AIS",
  0x0a:"NEXT",
  0x0b:"WAYPOINT",
  0x0c:"NORTH",
  0x0d:"ENTER"
}


class KM(object):
  def __init__(self,name,default,description=None):
    self.name=name
    self.description=description
    if self.description is None:
      self.description="Keymapping for key %s, refer to the AvNav doc for keyboard shortcuts"%self.name
    self.default=default
    self.type='STRING'
  def v(self):
    return self.__dict__

class Plugin(object):
  CONFIG=[
    {
      'name':'irqPin',
      'default': 11,
      'type': 'NUMBER',
      'description': 'the irq pin in board numbering (the default of 11 is GPIO17)'
    },
    {
      'name':'i2cAddress',
      'default': 0x14,
      'type': 'NUMBER',
      'description': 'the i2c address of the IR receiver'
    },
    {
      'name': 'allowRepeat',
      'default': False,
      'type':'BOOLEAN',
      'description': 'allow keys to repeat'
    },
    {
      'name': 'channel',
      'default':0,
      'type': 'SELECT',
      'description': 'the remote control channel to be used',
      'rangeOrList': ['0','1','2','3','4']
    }
  ]
  KM_PARAM=[
    KM(keyNames[0],'PageDown'),
    KM(keyNames[1],'PageUp'),
    KM(keyNames[2],'ArrowUp'),
    KM(keyNames[3],'ArrowLeft'),
    KM(keyNames[4],'ArrowRight'),
    KM(keyNames[5],'ArrowDown'),
    KM(keyNames[6],'t'),
    KM(keyNames[7],'d'),
    KM(keyNames[8],'q'),
    KM(keyNames[9],'a'),
    KM(keyNames[10],'n'),
    KM(keyNames[11],'Control-g'),
    KM(keyNames[12],'b'),
    KM(keyNames[13],'Enter')
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
    self.api.registerEditableParameters(
      self.CONFIG + list(map(lambda d: d.v(),self.KM_PARAM)),
      self.updateParam)
    self.api.registerRestart(self.stop)
    self.configSequence=0
    self.keyMap={}
    self.allowRepeat=False
    self.channel=0

  def _computeSettings(self):
    newKm={}
    for km in self.KM_PARAM:
      keyId=None
      for k,v in keyNames.items():
        if v == km.name:
          keyId=k
          break
      if keyId is None:
        continue
      mapping=self.api.getConfigValue(km.name,km.default)
      newKm[keyId]=mapping
    self.keyMap=newKm
    allowRepeat=self.api.getConfigValue('allowRepeat',False)
    if isinstance(allowRepeat,str):
      allowRepeat=allowRepeat.upper() == 'TRUE'
    self.allowRepeat=allowRepeat
    self.channel=int(self.api.getConfigValue('channel',0))


  def updateParam(self,newParam):
    self.api.saveConfigValues(newParam)
    self._computeSettings()


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
    self._computeSettings()
    self.api.setStatus('NMEA','running')
    i2c = smbus.SMBus(1)
    currentMode=gpio.getmode()
    if currentMode is None:
      gpio.setmode(gpio.BOARD)
    self.api.log("gpio mode=%d",gpio.getmode())
    lastIrq=None
    newIrq=False
    while not self.api.shouldStopMainThread():
      irqV=self.api.getConfigValue('irqPin',None)
      if irqV is None:
        #fallback old value
        irqV=self.api.getConfigValue('irgPin',11)
      irq=int(irqV)  
      if irq != lastIrq:
        try:
          self.api.debug("using irq pin %d",irq)
          gpio.setup(irq, gpio.IN)
          lastIrq=irq
          newIrq=True
        except Exception as e:
          self.api.setStatus('ERROR',"unable to set up pin %d: %s"%(irq,e))
          time.sleep(1)
          continue
      try:
        if newIrq:
          self.api.setStatus('NMEA','running using irq pin %d, channel %d'%(irq,self.channel))
          newIrq=False
        c=gpio.wait_for_edge(irq, gpio.RISING,timeout=1000)
        if c is None:
          continue
        address=int(self.api.getConfigValue('i2cAddress',0x14))
        keycode = i2c.read_byte(address)
        if self.allowRepeat:
          keycode=keycode & 0x3f
        v=self.keyMap.get(keycode)
        self.api.log("keycode=%d, translated=%s",keycode,v)
        if v is not None:
          self.api.sendRemoteCommand('K',v,channel=self.channel)
      except Exception as e:
        self.api.setStatus("ERROR","%s"%e)
        time.sleep(1)
        newIrq=True



