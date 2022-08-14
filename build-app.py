#!/usr/bin/python
# Compresses the files for one game into a single JavaScript file.
#
# Copyright 2013 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script generates two files:
#   compressed.js
#   uncompressed.js
# The compressed file is a concatenation of all the relevant JavaScript which
# has then been run through Google's Closure Compiler.
# The uncompressed file is a script that loads in each JavaScript file
# one by one.  This takes much longer for a browser to load, but is useful
# when debugging code since line numbers are meaningful and variables haven't
# been renamed.  The uncompressed file also allows for a faster development
# cycle since there is no need to rebuild or recompile, just reload.

import json
import os.path
import re
import subprocess
import sys
import threading

# Define a warning message for all the generated files.
WARNING = '// Automatically generated file.  Do not edit!\n'


blocklyMessageNames = []
blocklyGamesMessageNames = []

def main(name):
  if not os.path.exists('appengine/%s/generated' % name):
    os.mkdir('appengine/%s/generated' % name)
  compile(name)
  filterMessages(name)
  # Extract the list of supported languages from boot.js.
  # This is a bit fragile.
  boot = open('appengine/common/boot.js', 'r')
  js = ' '.join(boot.readlines())
  boot.close()
  m = re.search('\[\'BlocklyGamesLanguages\'\] = (\[[-,\'\\s\\w]+\])', js)
  if not m:
    raise Exception("Can't find BlocklyGamesLanguages in boot.js")
  langs = m.group(1)
  langs = langs.replace("'", '"')
  langs = json.loads(langs)
  for lang in langs:
    language(name, lang)


def filterMessages(name):
  global blocklyMessageNames, blocklyGamesMessageNames
  # Identify all the Blockly messages used.
  print("Scanning for Blockly messages in %s..." % name)
  f = open('appengine/%s/generated/compressed.js' % name, 'r')
  js = f.read()
  f.close()

  # Locate what Blockly.Msg has compiled into (e.g. h.Y)
  m = re.search('Blockly\.Msg=([\w.$]+)', js)
  if m:
    blocklyMsg = m.group(1)
    blocklyMsg = blocklyMsg.replace('.', '\\.').replace('$', '\\$')
    msgs1 = re.findall('\W' + blocklyMsg + '.([A-Z0-9_]+)', js)
    msgs2 = re.findall('\WBKY_([A-Z0-9_]+)', js)
    blocklyMessageNames = list(set(msgs1 + msgs2))
    # Resolve references.
    # Blockly.Msg["TEXT_APPEND_VAR"] = Blockly.Msg["VAR_DEFAULT_NAME"];
    # Does not handle long chains of references.
    msgs = getMessages('en')
    for msg in msgs:
      m = re.search('Blockly\.Msg\["([A-Z0-9_]+)"\] = Blockly\.Msg\["([A-Z0-9_]+)"\]', msg)
      if m and m.group(1) in blocklyMessageNames:
        blocklyMessageNames.append(m.group(2))
    print("Found %d Blockly messages." % len(blocklyMessageNames))
  else:
    print("Unable to find any Blockly messages.")
  blocklyMessageNames.sort()

  # Locate what BlocklyGames.Msg has compiled into (e.g. t.G)
  m = re.search('BlocklyGames\.Msg=([\w.$]+)', js)
  if m:
    blocklyGamesMsg = m.group(1)
    blocklyGamesMsg = blocklyGamesMsg.replace('.', '\\.').replace('$', '\\$')
    msgs = re.findall('\W' + blocklyGamesMsg + '\["([^"]+)"\]', js)
    msgs += re.findall('\W' + blocklyGamesMsg + '\.([\w$]+)', js)
    blocklyGamesMessageNames = list(set(msgs))
    print("Found %d Blockly Games messages." % len(blocklyGamesMessageNames))
  else:
    print("Unable to find any Blockly Games messages.")
  blocklyGamesMessageNames.sort()


def getMessages(lang):
  # Read all messages for this language.
  blocklyMsgFileName = 'appengine/generated/msg/%s.js' % lang
  f = open(blocklyMsgFileName, 'r')
  msgs = f.readlines()
  f.close()
  return msgs


def language(name, lang):
  global blocklyMessageNames, blocklyGamesMessageNames
  msgs = getMessages(lang)
  # Write copy to Blockly Games.
  if not os.path.exists('appengine/%s/generated/msg' % name):
    os.mkdir('appengine/%s/generated/msg' % name)
  f = open('appengine/%s/generated/msg/%s.js' % (name, lang), 'w')
  f.write(WARNING)
  f.write("'use strict';\n")
  for msg in msgs:
    # Only write out messages that are used (as detected in filterMessages).
    m = re.search('Blockly\.Msg\["([\w.]+)"\] = ', msg)
    if m and m.group(1) in blocklyMessageNames:
      f.write(msg)
    m = re.search('BlocklyGames\.Msg\["([\w.]+)"\] = ', msg)
    if m and m.group(1) in blocklyGamesMessageNames:
      f.write(msg)
  f.close()


def compile(name):
  print('Compiling %s' % name.title())
  # Run uncompressed and compressed code generation in separate threads.
  # For multi-core computers, this offers a significant speed boost.
  thread1 = Gen_uncompressed(name)
  thread2 = Gen_compressed(name)
  thread1.start()
  thread2.start()
  thread1.join()
  thread2.join()
  print("")


class Gen_uncompressed(threading.Thread):
  def __init__(self, name):
    threading.Thread.__init__(self)
    self.name = name

  def run(self):
    cmd = ['third-party/closurebuilder/closurebuilder.py',
        '--root=appengine/third-party/',
        '--root=appengine/generated/',
        '--root=appengine/js/',
        '--exclude=',
        '--namespace=%s' % self.name.replace('/', '.').title(),
        '--output_mode=list']
    directory = self.name
    while directory:
      subdir = 'appengine/%s/generated/' % directory
      if os.path.isdir(subdir):
        cmd.append('--root=%s' % subdir)
      subdir = 'appengine/%s/js/' % directory
      if os.path.isdir(subdir):
        cmd.append('--root=%s' % subdir)
      (directory, sep, fragment) = directory.rpartition(os.path.sep)
    try:
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except:
      raise Exception("Failed to Popen: %s" % ' '.join(cmd))
    files = readStdout(proc)

    if self.name == 'pond/docs':
      path = '../'
    else:
      path = ''
    prefix = 'appengine/'
    srcs = []
    for file in files:
      file = file.strip()
      if file[:len(prefix)] == prefix:
        file = file[len(prefix):]
      else:
        raise Exception('"%s" is not in "%s".' % (file, prefix))
      srcs.append('"%s%s"' % (path, file))
    srcs.append('"generated/msg/" + window[\'BlocklyGamesLang\'] + ".js"')
    f = open('appengine/%s/generated/uncompressed.js' % self.name, 'w')
    f.write("""%s
window.CLOSURE_NO_DEPS = true;

(function() {
  var srcs = [
      %s
  ];
  function loadScript() {
    var src = srcs.shift();
    if (src) {
      var script = document.createElement('script');
      script.src = src;
      script.type = 'text/javascript';
      script.onload = loadScript;
      document.head.appendChild(script);
    }
  }
  loadScript();
})();
""" % (WARNING, ',\n      '.join(srcs)))
    f.close()
    print('Found %d dependencies.' % len(srcs))


class Gen_compressed(threading.Thread):
  def __init__(self, name):
    threading.Thread.__init__(self)
    self.name = name

  def run(self):
    cmd = [
      'java',
      '-jar', 'third-party-downloads/closure-compiler.jar',
      '--generate_exports',
      '--compilation_level', 'ADVANCED_OPTIMIZATIONS',
      '--dependency_mode=PRUNE',
      '--externs', 'externs/gviz-externs.js',
      '--externs', 'externs/interpreter-externs.js',
      '--externs', 'externs/prettify-externs.js',
      '--externs', 'externs/soundJS-externs.js',
      '--externs', 'externs/storage-externs.js',
      '--externs', 'appengine/third-party/blockly/externs/svg-externs.js',
      #'--language_in', 'ECMASCRIPT5_STRICT',
      '--language_out', 'ECMASCRIPT5_STRICT',
      '--entry_point=%s' % self.name.replace('/', '.').title(),
      "--js='appengine/third-party/**.js'",
      #"--js='!appengine/third-party/base.js'",
      "--js='!appengine/third-party/blockly/externs/**.js'",
      "--js='appengine/generated/*.js'",
      "--js='appengine/js/*.js'",
      '--warning_level', 'QUIET',
    ]
    directory = self.name
    while directory:
      cmd.append("--js='appengine/%s/generated/*.js'" % directory)
      cmd.append("--js='appengine/%s/js/*.js'" % directory)
      (directory, sep, fragment) = directory.rpartition(os.path.sep)
    try:
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except:
      print("Failed to Popen: %s" % cmd)
      raise
    script = readStdout(proc)
    script = ''.join(script)
    script = self.trim_licence(script)
    print('Compressed to %d KB.' % (len(script) / 1024))

    f = open('appengine/%s/generated/compressed.js' % self.name, 'w')
    f.write(WARNING)
    f.write(script)
    # Load the chosen language pack.
    f.write("""
(function(){var s=document.createElement('script');
s.src='%s/generated/msg/'+window['BlocklyGamesLang']+'.js';
s.type='text/javascript';
document.head.appendChild(s);})();
""" % self.name)
    f.close()

  def trim_licence(self, code):
    """Strip out Google's and MIT's Apache licences.

    JS Compiler preserves dozens of Apache licences in the Blockly code.
    Remove these if they belong to Google or MIT.
    MIT's permission to do this is logged in Blockly issue 2412.

    Args:
      code: Large blob of compiled source code.

    Returns:
      Code with Google's and MIT's Apache licences trimmed.
    """
    apache2 = re.compile("""/\\*

 (Copyright \\d+ (Google LLC|Massachusetts Institute of Technology))
( All rights reserved.
)? SPDX-License-Identifier: Apache-2.0
\\*/""")
    return re.sub(apache2, '', code)


def readStdout(proc):
  data = proc.stdout.readlines()
  # Python 2 reads stdout as text.
  # Python 3 reads stdout as bytes.
  return list(map(lambda line:
      type(line) == str and line or str(line, 'utf-8'), data))


if __name__ == '__main__':
  if len(sys.argv) == 2:
    main(sys.argv[1])
  else:
    print('Format: %s <appname>' % sys.argv[0])
    sys.exit(2)
