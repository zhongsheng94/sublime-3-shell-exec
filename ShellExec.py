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

    view_ctx_map = []

    def __init__(self, view, output_view):

        self.view = view
        self.output_view = output_view

    def shell_exec_debug(self, text_message):
        if self.get_setting('debug'):
            print(text_message)

    def run_shell_command(self, command, args=None):

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

        command = sublime.expand_variables(
            command, sublime.active_window().extract_variables())

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

        full_command = "trap 'kill $(jobs -p) 2> /dev/null' EXIT;" + full_command

        self.shell_exec_debug('create Popen: executable=' +
                              self.get_setting('executable'))

        stderr = STDOUT

        cmd_line = [self.get_setting('executable')]
        cmd_line.extend(['--login', '-c'])
        cmd_line.append(full_command)

        lang = self.get_setting('lang')
        encoding = None
        env = os.environ.copy()
        if lang:
            encoding = lang.split('.')[1].lower()
            env['LANG'] = lang

        command_popen = Popen(cmd_line, shell=False,
                              env=env, stderr=stderr, stdout=PIPE)

        ShellExec.set_view_ctx_map(self.output_view, ShellExecContext(
            command, command_popen))

        self.view.window().focus_view(self.output_view)

        self.increment_output(" >  " + command + "\n\n")

        self.shell_exec_debug('waiting for stdout...')

        cmd_stdout_fd = io.TextIOWrapper(command_popen.stdout, encoding)

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

    def set_view_ctx_map(view, ctx):
        for pair in ShellExec.view_ctx_map:
            if view == pair[0]:
                pair[1] = ctx
                return
        ShellExec.view_ctx_map.append([view, ctx])


class ShellExecStop(sublime_plugin.TextCommand):

    def __init__(self, edit):
        sublime_plugin.TextCommand.__init__(self, edit)

    def run(self, edit, **args):
        for pair in ShellExec.view_ctx_map:
            if self.view == pair[0]:
                exec_ctx = pair[1]
                exec_ctx.get_command_popen().kill()
                print(exec_ctx.get_command() + ' stopped!')
                return


class ShellExecContext:
    """docstring for ShellExecContext"""

    def __init__(self, command, command_popen):
        self.command = command
        self.command_popen = command_popen

    def get_command(self):
        return self.command

    def get_command_popen(self):
        return self.command_popen
