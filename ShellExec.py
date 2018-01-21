import sys, io, time, sublime, sublime_plugin, re
from subprocess import Popen, PIPE, STDOUT
from threading import Thread


# class ShellExecRun(sublime_plugin.TextCommand):
#   def run(self, edit, **args):
#     # self.args = args

#     # if self.args.get('debug'):
#     #   print("\n\n>>>>>>>>>>>>>>>>>> Start Shell Exec Debug:")

#     # if not args.get("command"):
#     #   args["command"] = ""

#     if args.get("command"):
#       ShellExec(args, self.view).run_shell_command(args["command"])

class ShellExecOpen(sublime_plugin.TextCommand):
  def __init__(self, edit):
    sublime_plugin.TextCommand.__init__(self, edit);

    self.shell_exec = None

  def run(self, edit, **args):

    # if args.get('debug'):
    #   print("\n\n>>>>>>>>>>>>>>>>>> Start Shell Exec Debug:")

    def runShellExec(user_command):
      if self.shell_exec == None:
        self.shell_exec = ShellExec(self.view)
      self.shell_exec.run_shell_command(user_command)

    sublime.active_window().show_input_panel('Shell Exec', '', runShellExec, None, None)

class ShellExecViewInsertCommand(sublime_plugin.TextCommand):
  def run(self, edit, pos, text):
    self.view.insert(edit, pos, text)

class ShellExec:
  def __init__(self, view):

    self.view = view
    self.output_view = None
    self.panel_output = None

  def shell_exec_debug(self, text_message):
    if self.get_setting('debug'):
      print(text_message)

  # def command_variables(args, view, command, format=True):
    # if format and args.get("format"):
    #   command = args["format"].replace('${input}', command)

    # for region in view.sel():
    #   (row,col) = view.rowcol(view.sel()[0].begin())

    #   command = command.replace('${row}', str(row+1))
    #   command = command.replace('${region}', view.substr(region))
    #   break

    # packages, platform, file, file_path, file_name, file_base_name,
    # file_extension, folder, project, project_path, project_name,
    # project_base_name, project_extension.
    # command = sublime.expand_variables(command, sublime.active_window().extract_variables())

    # return command

  # def load_sh_file(source, path, args):
  #   if(path):
  #     try:
  #       with open(path, encoding='utf-8') as f:
  #         new_source = f.read()
  #         source += "\n" + new_source +  "\n"
          # if ShellExec.get_setting('debug', args):
          #   print(path + ' loaded:')
          #   print('------------------------------------')
          #   print(new_source)
          #   print('------------------------------------')
      #     return source
      # except:
      #   pass
        # if ShellExec.get_setting('debug', args):
        #   print(path + ' error: ' + str(sys.exc_info()[0]))

  def run_shell_command(self, command):

    command = sublime.expand_variables(command, sublime.active_window().extract_variables())

    # if 'folder' in sublime.active_window().extract_variables():
    #   if sublime.platform() == 'windows':
    #     pure_command = command.replace(sublime.active_window().extract_variables()['folder'] + '\\', '')
    #   else:
    #     pure_command = command.replace(sublime.active_window().extract_variables()['folder'] + '/', '')
    # else:
    #   pure_command = command


    # sublime_shell_source = ''

    # sh_file_settings = self.get_setting('load_sh_file', True)
    # sh_file_shortcut = self.get_setting('load_sh_file', False)

    # sublime_shell_source = ShellExec.load_sh_file(sublime_shell_source, sh_file_settings, self.args)

    # if sh_file_settings != sh_file_shortcut:
    #   sublime_shell_source = ShellExec.load_sh_file(sublime_shell_source, sh_file_shortcut, self.args)


    self.shell_exec_debug('new Thread')

    t = Thread(target=ShellExec.execute_shell_command, args=(self, command))
    t.start()

  def new_output_view(self):
    self.shell_exec_debug('open new empty file: ')

    output_view = sublime.active_window().new_file()
    output_view.set_name('Shell Exec')
    output_view.set_scratch(True)

    if self.get_setting('output_syntax'):
      self.shell_exec_debug('set output syntax: ' + self.get_setting('output_syntax'))

      if sublime.find_resources(self.get_setting('output_syntax') + '.tmLanguage'):
        output_view.set_syntax_file(sublime.find_resources(self.get_setting('output_syntax') + '.tmLanguage')[0])

    if self.get_setting('output_word_wrap'):
      output_view.settings().set('word_wrap', True)
    else:
      output_view.settings().set('word_wrap', False)

    return output_view

  def increment_output(self, text):
    if self.get_setting('output') == "file":
      if not (self.output_view and self.output_view in self.view.window().views()):
        self.output_view = self.new_output_view()

      self.output_view.run_command('shell_exec_view_insert', {'pos': self.output_view.size(), 'text': text})
    # elif self.get_setting('output') == "none":
    #   self.panel_output = False
    # else:
    #   if not self.panel_output:
    #     self.panel_output = True
    #     sublime.active_window().run_command('show_panel', {"panel": "console", "toggle": False})
    #   sys.stdout.write(text)

  def execute_shell_command(self, command):

    self.shell_exec_debug("run command: " + command)

    full_command = command

    if self.get_setting('context') == 'project_folder' and 'folder' in sublime.active_window().extract_variables():
        full_command = "cd '" + sublime.active_window().extract_variables()['folder'] + "' && " + command
    if self.get_setting('context') == 'file_folder' and 'file_path' in sublime.active_window().extract_variables():
        full_command = "cd '" + sublime.active_window().extract_variables()['file_path'] + "' && " + command


    self.shell_exec_debug('create Popen: executable=' + self.get_setting('executable'))

    stderr = STDOUT

    cmd_line = self.get_setting('executable').split()
    cmd_line.extend(['--login', '-c'])
    cmd_line.append(full_command)

    encoding = self.get_setting('encoding')
    if encoding:
      env = os.environ.copy()
      if 'LANG' in env:
        env['LANG'] = env['LANG'].split('.')[0] + '.' + encoding.upper()
      else:
        env['LANG'] = 'en_US.' + encoding.upper()

    console_command = Popen(cmd_line, shell=False, env=env, stderr=stderr, stdout=PIPE)

    self.increment_output(" >  " + command + "\n\n")

    self.shell_exec_debug('waiting for stdout...')


    cmd_stdout_fd = io.TextIOWrapper(console_command.stdout, encoding)

    while True:
      output = cmd_stdout_fd.readline(1024)
      if output == '':
        break

      self.shell_exec_debug('send result to output file.')
      self.increment_output(output)

    self.increment_output('\n\n')

    self.view.window().focus_view(self.output_view)

    self.shell_exec_debug(">>>>>>>>>>>>>>>>>> Shell Exec Debug Finished!")

    sublime.status_message('Shell Exec | Done! > ' + command[0:60])

  def get_setting(self, name):

    settings = sublime.load_settings('Preferences.sublime-settings')
    if settings.get('shell_exec_' + name):
      return settings.get('shell_exec_' + name)
    else:
      settings = sublime.load_settings('ShellExec.sublime-settings')
      return settings.get('shell_exec_' + name)
