import os
import socket
import signal
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

    exec_contexts = []

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

        self.view.window().focus_view(self.output_view)
        self.increment_output(" >  " + command + "\n\n")
        self.shell_exec_debug('waiting for stdout...')

        cmd_line = self.package_cmd_line(command)

        Popen(cmd_line, shell=False,
              env=self.get_exec_environment(), stderr=STDOUT, stdout=PIPE)
        self.shell_exec_debug('create Popen: executable=' +
                              self.get_setting('executable'))

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', self.get_setting('listen_port')))
        socket_file = s.makefile(encoding=self.get_setting('encoding'))

        ShellExec.add_context(ShellExecContext(self.output_view, socket_file, s))

        self.shell_exec_debug('send result to output file.')

        while True:
            output = socket_file.read(1024)
            if not output:
                break
            self.increment_output(output)
            self.scroll_to_end()

        socket_file.close()
        s.close()
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

    def add_context(ctx):
        if ctx in ShellExec.exec_contexts:
            ctx_index = ShellExec.exec_contexts.index(ctx)
            ShellExec.exec_contexts[ctx_index] = ctx
        else:
            ShellExec.exec_contexts.append(ctx)

    def package_cmd_line(self, command):
        sublime_vars = sublime.active_window().extract_variables()

        command = sublime.expand_variables(
            command, sublime_vars)
        if (self.get_setting('context') == 'project_folder' and
                'folder' in sublime_vars):
            command = "cd '" + \
                sublime_vars['folder'] + "' && " + command

        if (self.get_setting('context') == 'file_folder' and
                'file_path' in sublime_vars):
            command = "cd '" + \
                sublime_vars['file_path'] + "' && " + command

        lten_port = self.get_setting('listen_port')
        socat_head = 'socat TCP4-LISTEN:%d,bind=127.0.0.1' % (lten_port)
        socat_cmd_line = socat_head.split() + ['SYSTEM:' + command]
        cmd_line = [self.get_setting('executable')] + socat_cmd_line
        return cmd_line

    def get_exec_environment(self):
        env = os.environ.copy()
        extra_env = self.get_setting('environment')
        env.update(extra_env)
        return env


class ShellExecStop(sublime_plugin.TextCommand):

    def __init__(self, edit):
        sublime_plugin.TextCommand.__init__(self, edit)

    def run(self, edit, **args):
        for ctx in ShellExec.exec_contexts:
            if self.view == ctx.view:
                ctx.socket_fd.close()
                ctx.socket_file.close()


class ShellExecContext:
    """docstring for ShellExecContext"""

    def __init__(self, view, socket_file, socket_fd):
        self.view = view
        self.socket_file = socket_file
        self.socket_fd = socket_fd

    def __eq__(self, other):
        return self.view == other.view
