import os
import io
import sublime
import sublime_plugin
from subprocess import Popen, PIPE, STDOUT
from threading import Thread


class ShellExecViewInsertCommand(sublime_plugin.TextCommand):
    def run(self, edit, pos, text):
        self.view.insert(edit, pos, text)


class ShellExecOpen(sublime_plugin.TextCommand):
    def __init__(self, edit):
        sublime_plugin.TextCommand.__init__(self, edit)
        self.output_view = None

    def run(self, edit, **args):

        def runShellExec(user_command):
            if not (self.output_view and
                    self.output_view in self.view.window().views()):
                self.output_view = sublime.active_window().new_file()
            ShellExec(self.view, self.output_view).run_shell_command(
                user_command)

            sublime.active_window().show_input_panel(
                'Shell Exec', '', runShellExec, None, None)


class ShellExec:

    def __init__(self, view, output_view):

        self.view = view
        self.output_view = output_view

    def shell_exec_debug(self, text_message):
        if self.get_setting('debug'):
            print(text_message)

    def run_shell_command(self, command, args=None):

        command = sublime.expand_variables(
            command, sublime.active_window().extract_variables())

        self.shell_exec_debug('new Thread')

        t = Thread(target=ShellExec.execute_shell_command,
                   args=(self, command))
        t.start()

    def set_output_view(self):
        self.shell_exec_debug('open new empty file: ')

        self.output_view.set_name('Shell Exec')
        self.output_view.set_scratch(True)

        if self.get_setting('output_syntax'):
            self.shell_exec_debug('set output syntax: ' +
                                  self.get_setting('output_syntax'))

            if sublime.find_resources(self.get_setting('output_syntax') +
                                      '.tmLanguage'):

                self.output_view.set_syntax_file(sublime.find_resources(
                    self.get_setting('output_syntax') + '.tmLanguage')[0])

        if self.get_setting('output_word_wrap'):
            self.output_view.settings().set('word_wrap', True)
        else:
            self.output_view.settings().set('word_wrap', False)

        return self.output_view

    def increment_output(self, text):
        self.set_output_view()

        self.output_view.run_command('shell_exec_view_insert',
                                     {'pos': self.output_view.size(),
                                      'text': text})

    def scroll_to_end(self):
        self.output_view.show(self.output_view.size())

    def execute_shell_command(self, command):

        self.shell_exec_debug("run command: " + command)

        full_command = command

        if (self.get_setting('context') == 'project_folder' and
                'folder' in sublime.active_window().extract_variables()):
            full_command = "cd '" + \
                sublime.active_window().extract_variables()[
                    'folder'] + "' && " + command

        if (self.get_setting('context') == 'file_folder' and
                'file_path' in sublime.active_window().extract_variables()):
            full_command = "cd '" + \
                sublime.active_window().extract_variables()[
                    'file_path'] + "' && " + command

        self.shell_exec_debug('create Popen: executable=' +
                              self.get_setting('executable'))

        stderr = STDOUT

        cmd_line = self.get_setting('executable').split()
        cmd_line.extend(['--login', '-c'])
        cmd_line.append(full_command)

        encoding = self.get_setting('encoding')

        env = os.environ.copy()
        if encoding:
            if 'LANG' in env:
                env['LANG'] = env['LANG'].split(
                    '.')[0] + '.' + encoding.upper()
            else:
                env['LANG'] = 'en_US.' + encoding.upper()

        console_command = Popen(cmd_line, shell=False,
                                env=env, stderr=stderr, stdout=PIPE)

        self.increment_output(" >  " + command + "\n\n")

        self.shell_exec_debug('waiting for stdout...')

        cmd_stdout_fd = io.TextIOWrapper(console_command.stdout, encoding)

        while True:
            output = cmd_stdout_fd.readline(1024)
            if output == '':
                break

            self.shell_exec_debug('send result to output file.')
            self.increment_output(output)
            self.scroll_to_end()

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
