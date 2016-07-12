#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import tempfile
import os.path

"""
test_task
----------------------------------

Tests for `task` module.
"""

import shutil
import platform
import os
import stat

from d3r.celpp.task import D3RParameters
from d3r.celpp.task import UnsetPathError
from d3r.celpp.task import UnsetStageError
from d3r.celpp.task import UnsetNameError
from d3r.celpp.task import UnsetCommandError
from d3r.celpp.task import UnsetFileNameError
from d3r.celpp.task import D3RTask
from d3r.celpp.filetransfer import FtpFileTransfer


class MockException(Exception):
    pass


class MockFileTransfer(FtpFileTransfer):
    """Fake FileUploader
    """
    def __init__(self):
        self._upload_files_except_object = None
        self._upload_summary_except_object = None
        self._upload_summary = None
        self._upload_files = None
        self._connect = True

    def set_upload_files(self, val):
        self._upload_files = val

    def set_upload_files_exception(self, except_object):
        self._upload_files_except_object = except_object

    def upload_files(self, list_of_files):
        """

        :param list_of_files:
        :return:
        """
        if self._upload_files_except_object is not None:
            raise self._upload_files_except_object
        return self._upload_files

    def set_upload_summary(self, val):
        self._upload_summary = val

    def set_upload_summary_exception(self, except_object):
        self._upload_summary_except_object = except_object

    def get_upload_summary(self):
        """

        :return: String set in set_upload_summary()
        """
        if self._upload_summary_except_object is not None:
            raise self._upload_summary_except_object

        return self._upload_summary

    def set_connect(self, val):
        self._connect = val

    def connect(self):
        return self._connect

    def disconnect(self):
        pass


class TestD3rTask(unittest.TestCase):

    def setUp(self):
        pass

    def test_constructor(self):
        params = D3RParameters()
        task = D3RTask('/path', params)
        self.assertEqual(task.get_name(), None)
        self.assertEqual(task.get_path(), '/path')
        self.assertEqual(task.get_stage(), None)
        self.assertEqual(task.get_status(), D3RTask.UNKNOWN_STATUS)
        self.assertEqual(task.get_error(), None)
        task.set_name('foo')
        task.set_path('blah')
        task.set_stage(4)
        task.set_status(D3RTask.START_STATUS)
        task.set_error('error')
        task.set_file_transfer('yah')

        self.assertEqual(task.get_name(), 'foo')
        self.assertEqual(task.get_path(), 'blah')
        self.assertEqual(task.get_stage(), 4)
        self.assertEqual(task.get_status(), D3RTask.START_STATUS)
        self.assertEqual(task.get_error(), 'error')
        self.assertEqual(task.get_file_transfer(), 'yah')

        params.ftpconfig = '/somefile'
        task = D3RTask('/path', params)
        self.assertEqual(task.get_file_transfer(), None)

    def test_get_dir_name(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        try:
            task.get_dir_name()
            self.fail('Expected UnsetStageError')
        except UnsetStageError:
            pass

        task.set_stage(1)
        try:
            task.get_dir_name()
            self.fail('Expected UnsetNameError')
        except UnsetNameError:
            pass

        task.set_name('foo')
        self.assertEqual(task.get_dir_name(), 'stage.1.foo')

    def test_get_dir(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        try:
            task.get_dir()
            self.fail('Expected UnsetPathError')
        except UnsetPathError:
            pass

        task.set_path('/blah')

        try:
            task.get_dir()
            self.fail('Expected UnsetStageError')
        except UnsetStageError:
            pass

        task.set_stage(1)
        try:
            task.get_dir()
            self.fail('Expected UnsetNameError')
        except UnsetNameError:
            pass

        task.set_name('foo')

        self.assertEqual(task.get_dir(), '/blah/stage.1.foo')

    def test_get_set_email_log(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        self.assertEqual(task.get_email_log(), None)
        task.set_email_log('hi')
        self.assertEqual(task.get_email_log(), 'hi')

    def test_get_program_name(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        self.assertTrue(task._get_program_name().find('task.py') > 0,
                        task._get_program_name())
        params.program = 'proggy'
        params.version = 'versy'
        task = D3RTask(None, params)
        self.assertEqual(task._get_program_name(), 'proggy versy')

    def test_get_uploadable_files(self):
        task = D3RTask(None, D3RParameters())
        self.assertEqual(task.get_uploadable_files(), [])
        temp_dir = tempfile.mkdtemp()
        try:
            task = D3RTask(temp_dir, D3RParameters())
            task.set_stage(1)
            task.set_name('foo')
            task.create_dir()
            self.assertEqual(task.get_uploadable_files(), [])

            # add error file
            err_file = os.path.join(task.get_dir(), D3RTask.ERROR_FILE)
            open(err_file, 'a').close()
            flist = task.get_uploadable_files()
            self.assertEqual(len(flist), 1)
            self.assertEqual(flist[0], err_file)

            # add stderr file
            foostderr = os.path.join(task.get_dir(), 'foo.stderr')
            open(foostderr, 'a').close()
            flist = task.get_uploadable_files()
            flist.index(err_file)
            flist.index(foostderr)
            self.assertEqual(len(flist), 2)

            # add stdout file
            foostdout = os.path.join(task.get_dir(), 'foo.stdout')
            open(foostdout, 'a').close()
            flist = task.get_uploadable_files()
            self.assertEqual(len(flist), 3)
            flist.index(err_file)
            flist.index(foostderr)
            flist.index(foostdout)
        finally:
            shutil.rmtree(temp_dir)

    def test_can_run(self):
        task = D3RTask(None, D3RParameters())
        self.assertEqual(task.can_run(), False)

    def test_upload_task(self):
        task = D3RTask(None, D3RParameters())
        self.assertEqual(task._file_uploader, None)
        # try calling upload_task where _file_uploader is None
        task._upload_task()

        # try calling upload_task where _file_uploader is NOT None
        params = D3RParameters()
        params.ftpconfig = 'foo'
        task = D3RTask(None, params)
        self.assertEqual(task._file_uploader, None)
        # try calling upload_task where _file_uploader is None
        task._upload_task()

        # try calling upload_task where _file_uploader.upload_files
        # throws exception
        uploader = MockFileTransfer()
        uploader.set_upload_files_exception(MockException('hi'))
        task = D3RTask(None, D3RParameters())
        task.set_file_transfer(uploader)
        task._upload_task()

        # try calling where upload_summary throws exception
        uploader.set_upload_files_exception(None)
        uploader.set_upload_summary_exception(MockException('boo'))
        task._upload_task()

        # try calling where upload_summary returns None
        uploader.set_upload_summary_exception(None)
        uploader.set_upload_summary(None)
        task._upload_task()

        uploader.set_upload_summary('hello')
        task._upload_task()
        self.assertEqual(task._email_log, '\nhello\n')

    def test_run(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        self.assertEqual(task._can_run, None)
        task.run()
        self.assertEqual(task._can_run, False)
        task._can_run = True

        temp_dir = tempfile.mkdtemp()
        task.set_name('foo')
        task.set_stage(1)
        task.set_path(temp_dir)
        try:
            task.run()
        finally:
            shutil.rmtree(temp_dir)

    def test_write_to_file(self):
        tempDir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(None, params)
            try:
                task.write_to_file('hello', None)
                self.fail('Expected UnsetFileNameError')
            except UnsetFileNameError:
                pass
            try:
                task.write_to_file('hello', 'foo')
                self.fail('Expected UnsetPathError')
            except UnsetPathError:
                pass
            task.set_name('foo')
            task.set_stage(1)
            task.set_path(tempDir)

            try:
                task.write_to_file('hello', 'foo')
                self.fail('Expected IOError')
            except IOError:
                pass
            task.create_dir()
            task.write_to_file('hello', 'foo')
            self.assertEqual(os.path.isfile(os.path.join(task.get_dir(),
                                            'foo')), True)
        finally:
            shutil.rmtree(tempDir)

    def test_create_dir(self):
        tempDir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(None, params)
            try:
                task.create_dir()
                self.fail('Expected UnsetPathError')
            except UnsetPathError:
                pass
            task.set_name('foo')
            task.set_stage(1)
            task.set_path(tempDir)
            self.assertEqual(task.create_dir(),
                             os.path.join(tempDir, 'stage.1.foo'))
        finally:
            shutil.rmtree(tempDir)

    def test_update_status_from_filesystem(self):
        params = D3RParameters()
        task = D3RTask(None, params)

        try:
            task.update_status_from_filesystem()
            self.fail("Expected UnsetPathError")
        except UnsetPathError:
            pass

        tempDir = tempfile.mkdtemp()
        try:
            task.set_path(tempDir)

            # Test unset stage
            try:
                task.update_status_from_filesystem()
                self.fail("Expected UnsetStageError")
            except UnsetStageError:
                pass
        finally:
            shutil.rmtree(tempDir)

        task.set_stage(1)
        task.set_name('foo')

        try_update_status_from_filesystem(self, task)

    def test_start(self):
        temp_dir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(temp_dir, params)
            task.set_stage(1)
            task.set_name('foo')
            task.start()
            self.assertEqual(os.path.isfile(os.path.join(task.get_dir(),
                                            D3RTask.START_FILE)), True)
            self.assertEqual(task.get_error(), None)
            self.assertEqual(task.get_status(), D3RTask.START_STATUS)
            task.start()
            self.assertNotEqual(task.get_error(), None)
            self.assertEqual(task.get_status(), D3RTask.ERROR_STATUS)
            self.assertEqual(os.path.isfile(os.path.join(task.get_dir(),
                                                         D3RTask
                                                         .ERROR_FILE)), True)

        finally:
            shutil.rmtree(temp_dir)

    def test_end(self):
        temp_dir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(temp_dir, params)
            task.set_stage(1)
            task.set_name('foo')
            task.start()
            task.end()
            self.assertEqual(os.path.isfile(os.path.join(task.get_dir(),
                                                         D3RTask.
                                                         COMPLETE_FILE)), True)
            self.assertEqual(task.get_error(), None)
            self.assertEqual(task.get_status(), D3RTask.COMPLETE_STATUS)
            task.set_error('some error')
            task.end()
            self.assertEqual(task.get_error(), 'some error')
            self.assertEqual(task.get_status(), D3RTask.ERROR_STATUS)

            err_file = os.path.join(task.get_dir(), D3RTask.ERROR_FILE)

            self.assertEqual(os.path.isfile(err_file), True)
            f = open(err_file, 'r')
            err_msg = f.readline()
            self.assertEqual(err_msg, 'some error\n')
            task.set_status(D3RTask.ERROR_STATUS)
            os.remove(err_file)
            task.set_error(None)
            task.end()
            self.assertEqual(task.get_status(), D3RTask.ERROR_STATUS)
            self.assertEqual(os.path.isfile(err_file), True)
            self.assertEqual(os.path.getsize(err_file), 0)

        finally:
            shutil.rmtree(temp_dir)

    def test_get_smtp_server(self):
        params = D3RParameters()
        params.smtp = ''
        params.smtpport = '25'
        task = D3RTask(None, params)
        self.assertNotEqual(task._get_smtp_server(), None)

    def test_build_from_address(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        exp_from_addr = os.getlogin() + '@' + platform.node()
        self.assertEqual(task._build_from_address(), exp_from_addr)

    def test_run_external_command_all_params_None(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        try:
            task.run_external_command(None, None, None)
            self.fail('expected UnsetNameError')
        except UnsetNameError:
            pass

    def test_run_external_command_name_None(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        try:
            task.run_external_command(None, 'true', None)
            self.fail('expected UnsetNameError')
        except UnsetNameError:
            pass

    def test_run_external_command_name_cmd_to_run_None(self):
        params = D3RParameters()
        task = D3RTask(None, params)
        try:
            task.run_external_command('hello', None, None)
            self.fail('expected UnsetCommandError')
        except UnsetCommandError:
            pass

    def test_run_external_command_name_failure_is_fatal_is_None(self):
        temp_dir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(None, params)
            task.set_name('foo')
            task.set_stage(1)
            task.set_path(temp_dir)
            task.create_dir()
            task.set_path(temp_dir)
            self.assertEquals(1, task.run_external_command('hi',
                                                           'false',
                                                           None))
            self.assertEquals(task.get_error(), 'Non zero exit code:' +
                              ' 1 received. Standard out:  Standard error: ')
            self.assertEquals(task.get_status(), D3RTask.ERROR_STATUS)
        finally:
            shutil.rmtree(temp_dir)

    def test_run_external_command_cmd_raises_exception(self):
        temp_dir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(None, params)
            task.set_name('foo')
            task.set_stage(1)
            task.set_path(temp_dir)
            task.create_dir()
            task.set_path(temp_dir)
            self.assertEquals(1, task.run_external_command('hi',
                                                           'asdfasdf',
                                                           None))
            self.assertEquals(task.get_error(), 'Caught Exception trying ' +
                              'to run asdfasdf : [Errno 2] No such file ' +
                              'or directory')

            self.assertEquals(os.path.exists(os.path.join(task.get_dir(),
                                                          'hi.stdout')),
                              False)
            self.assertEquals(os.path.exists(os.path.join(task.get_dir(),
                                                          'hi.stderr')),
                              False)

        finally:
            shutil.rmtree(temp_dir)

    def test_run_external_command_cmd_fails_and_is_fatal(self):
        temp_dir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(None, params)
            task.set_name('foo')
            task.set_stage(1)
            task.set_path(temp_dir)
            task.create_dir()
            task.set_path(temp_dir)
            self.assertEquals(1, task.run_external_command('hi',
                                                           'false',
                                                           True))
            self.assertEquals(task.get_error(), 'Non zero exit code:' +
                              ' 1 received. Standard out:  Standard error: ')
            self.assertEquals(task.get_status(), D3RTask.ERROR_STATUS)
        finally:
            shutil.rmtree(temp_dir)

    def test_run_external_command_cmd_fails_and_isnot_fatal(self):
        temp_dir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(None, params)
            task.set_name('foo')
            task.set_stage(1)
            task.set_path(temp_dir)
            task.create_dir()
            task.set_path(temp_dir)
            self.assertEquals(1, task.run_external_command('hi',
                                                           'false',
                                                           False))
            self.assertEquals(task.get_error(), None)
            self.assertEquals(task.get_status(), D3RTask.UNKNOWN_STATUS)
        finally:
            shutil.rmtree(temp_dir)

    def test_run_external_command_cmd_succeeds(self):
        temp_dir = tempfile.mkdtemp()
        try:
            params = D3RParameters()
            task = D3RTask(None, params)
            task.set_name('foo')
            task.set_stage(1)
            task.set_path(temp_dir)
            task.create_dir()
            task.set_path(temp_dir)
            self.assertEquals(0, task.run_external_command('hi',
                                                           'echo hi',
                                                           False))
            self.assertEquals(task.get_error(), None)
            self.assertEquals(task.get_status(), D3RTask.UNKNOWN_STATUS)
            self.assertEquals(os.path.exists(os.path.join(task.get_dir(),
                                                          'hi.stdout')),
                              True)
            self.assertEquals(os.path.exists(os.path.join(task.get_dir(),
                                                          'hi.stderr')),
                              True)

        finally:
            shutil.rmtree(temp_dir)

    def tearDown(self):
        pass


def try_update_status_from_filesystem(self, task):
    """Runs various tests on update_status_filesystem method
    This is a function cause this needs to be tested on
    all the subclasses as well
    """
    tempDir = tempfile.mkdtemp()
    try:
        task.set_path(tempDir)

        self.assertEqual(task.update_status_from_filesystem(),
                         D3RTask.NOTFOUND_STATUS)

        self.assertEqual(task.get_status(),
                         D3RTask.NOTFOUND_STATUS)

        # Test directory exists but no complete, start, or error files
        task.create_dir()
        self.assertEqual(task.update_status_from_filesystem(),
                         D3RTask.UNKNOWN_STATUS)

        self.assertEqual(task.get_status(),
                         D3RTask.UNKNOWN_STATUS)

        # Test start file exists
        startFile = os.path.join(tempDir, task.get_dir_name(),
                                 'start')
        open(startFile, 'a').close()

        self.assertEqual(task.update_status_from_filesystem(),
                         D3RTask.START_STATUS)

        self.assertEqual(task.get_status(),
                         D3RTask.START_STATUS)

        # Test error file exists
        errorFile = os.path.join(tempDir, task.get_dir_name(),
                                 'error')
        open(errorFile, 'a').close()

        self.assertEqual(task.update_status_from_filesystem(),
                         D3RTask.ERROR_STATUS)

        self.assertEqual(task.get_status(),
                         D3RTask.ERROR_STATUS)

        # Test complete file exists
        completeFile = os.path.join(tempDir, task.get_dir_name(),
                                    'complete')
        open(completeFile, 'a').close()

        self.assertEqual(task.update_status_from_filesystem(),
                         D3RTask.COMPLETE_STATUS)

        self.assertEqual(task.get_status(),
                         D3RTask.COMPLETE_STATUS)

    finally:
        shutil.rmtree(tempDir)


if __name__ == '__main__':
    unittest.main()
