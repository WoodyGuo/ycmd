#!/usr/bin/env python
#
# Copyright (C) 2015 Google Inc.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging
import os
import subprocess
import sys
import threading

from ycmd import utils
from ycmd import responses
from ycmd.completers.completer import Completer

from DartAnalysisServer import DartAnalysisServer
from DartAnalysisServerListener import DartAnalysisServerListener

DART_FILETYPES = set(["dart"])

_logger = logging.getLogger(__name__)

reload(sys)
sys.setdefaultencoding("utf-8")


def PathToDartBinFolder(user_options):
    bin_folder = user_options.get("dart_bin_folder_path")
    if not bin_folder:
        dart_binary = utils.PathToFirstExistingExecutable(["dart"])
        if dart_binary:
            bin_folder = os.path.dirname(dart_binary)

    if not bin_folder or os.path.basename(bin_folder) != "bin":
        raise RuntimeError("Dart-sdk bin folder not found, please specify "
                           "g:ycm_path_to_dart_bin_folder in your .vimrc")
    return bin_folder


_condition = threading.Condition()


class MyListener(DartAnalysisServerListener):

    def on_server_ready(self, version, pid):
        _logger.info("server %s started: %i", version, pid)

    def on_server_error(self, error):
        _logger.info("server error: %s" % error)

    def on_response_available(self, response):
        with _condition:
            global response_json
            response_json = json.load(response)
            _condition.notifyAll()


class AnalysisService(object):

    def __init__(self, user_options):
        dart_bin_path = PathToDartBinFolder(user_options)
        self._cpp_server = DartAnalysisServer.create(dart_bin_path, None)
        self._listener = MyListener()
        self._cpp_server.start(_listener)

    def Kill(self):
        self._cpp_server.stop()

    def SetAnalysisRoots(self, included, excluded, packageRoots):
        self._cpp_server.set_analysis_roots(included, excluded, package_roots)

    def SetPriorityFiles(self, files):
        self._cpp_server.set_priority_files(files)

    def UpdateFileContent(self, filename, content):
        self._cpp_server.update_content(file, content)

    def GetErrors(self, filename):
        return None

    def GetNavigation(self, filename, offset, length):
        return None

    def GetHover(self, filename, offset):
        return None

    def GetSuggestions(self, filename, offset):
        result_id = self._cpp_server.get_suggestions(filename, offset)
        results = []
        with _condition:
            _condition.wait()
            if (("event" in response_json) and (response_json["event"] == result_type) and
                (response_json["params"]["id"] == result_id)):
                _logger.info("got result!")
                params = response_json["params"]
                results.extend(params["results"])
                if params["isLast"]:
                    return results


class RequestData(object):

    def __init__(self, request_data):
        self.filename = request_data["filepath"]
        self.contents = request_data["file_data"][self.filename]["contents"]
        self.line = request_data["line_num"]
        self.column = request_data["column_num"]
        self.offset = _ComputeOffset(self.contents, self.line, self.column)


class DartCompleter(Completer):

    _subcommands = {
        "GoToDefinition": lambda self, data: self._GoToDefinition(data),
        "GetType": lambda self, data: self._GetType(data),
    }

    def __init__(self, user_options):
        super(DartCompleter, self).__init__(user_options)
        self._service = AnalysisService(user_options)
        self._roots = []
        self._priority_files = []

    def DefinedSubcommands(self):
        return DartCompleter._subcommands.keys()

    def OnUserCommand(self, arguments, request_data):
        if not arguments:
            raise ValueError(self.UserCommandsHelpMessage())
        command_name = arguments[0]
        if command_name in DartCompleter._subcommands:
            command = DartCompleter._subcommands[command_name]
            return command(self, request_data)
        else:
            raise ValueError(self.UserCommandsHelpMessage())

    def SupportedFiletypes(self):
        return DART_FILETYPES

    def _EnsureFileInAnalysisServer(self, filename):
        _logger.info("enter buffer: %s " % filename)

        directory = os.path.dirname(filename)
        while (not os.path.exists(os.path.join(directory, "pubspec.yaml")) and directory != "" and
               directory != "/"):
            directory = os.path.dirname(directory)

        if directory == "" or directory == "/":
            directory = os.path.dirname(filename)

        if directory not in self._roots:
            self._roots.append(directory)
            self._service.SetAnalysisRoots(self._roots, [], {})
            _logger.info("added root: %s " % directory)

        if filename not in self._priority_files:
            self._priority_files.append(filename)
            self._service.SetPriorityFiles(self._priority_files)
            _logger.info("added priority file: %s " % filename)

    def OnBufferVisit(self, request_data):
        self._EnsureFileInAnalysisServer(request_data["filepath"])

    def OnFileReadyToParse(self, request_data):
        filename = request_data["filepath"]
        self._EnsureFileInAnalysisServer(filename)
        contents = request_data["file_data"][filename]["contents"]
        self._service.UpdateFileContent(filename, contents)
        return self._GetErrorsResponseToDiagnostics(contents, self._service.GetErrors(filename))

    def ComputeCandidatesInner(self, request_data):
        r = RequestData(request_data)
        self._service.UpdateFileContent(r.filename, r.contents)
        return self._SuggestionsToCandidates(self._service.GetSuggestions(r.filename, r.offset))

    def Shutdown(self):
        self._service.Kill()

    def _GoToDefinition(self, request_data):
        r = RequestData(request_data)
        result = self._service.GetNavigation(r.filename, r.offset, 1)
        _logger.info("navigation: %s " % result)
        if "targets" in result and "files" in result:
            target = result["targets"][0]
            filepath = result["files"][target["fileIndex"]]
            _logger.info("jump to: %s " % target)
            return responses.BuildGoToResponse(filepath, target["startLine"], target["startColumn"])
        else:
            raise RuntimeError("Can\"t jump to definition")

    def _GetType(self, request_data):
        r = RequestData(request_data)
        result = self._service.GetHover(r.filename, r.offset)
        if result["hovers"]:
            hover = result["hovers"][0]
            if "propagatedType" in hover:
                return {"message": hover["propagatedType"]}
            elif "elementDescription" in hover:
                description = self._ToAscii(hover["elementDescription"])
                return {"message": description}
            else:
                raise Exception("unknown type")
        else:
            raise Exception("unknown type")

    def _GetErrorsResponseToDiagnostics(self, contents, response):
        result = []
        for error in response["errors"]:
            location = error["location"]
            end_line, end_col = _ComputeLineAndColumn(contents,
                                                      location["offset"] + location["length"])
            result.append({
                "location": {
                    "line_num": location["startLine"],
                    "column_num": location["startColumn"],
                    "filepath": location["file"]
                },
                "location_extent": {
                    "start": {
                        "line_num": location["startLine"],
                        "column_num": location["startColumn"]
                    },
                    "end": {
                        "line_num": end_line,
                        "column_num": end_col
                    }
                },
                "ranges": [],
                "text": error["message"],
                "kind": error["severity"]
            })
        return result

    def _ToAscii(self, str):
        result = str.replace(u"\u2192", "->")
        return result.decode("utf-8").encode("ascii", "ignore")

    def _SuggestionsToCandidates(self, suggestions):
        result = []
        suggestions.sort(key=lambda s: -s["relevance"])
        for suggestion in suggestions:
            entry = {"insertion_text": suggestion["completion"]}
            if "returnType" in suggestion:
                entry["extra_menu_info"] = suggestion["returnType"]
            result.append(entry)
        return result


def _ComputeLineAndColumn(contents, offset):
    curline = 1
    curcol = 1
    for i, byte in enumerate(contents):
        if i == offset:
            return (curline, curcol)
        curcol += 1
        if byte == "\n":
            curline += 1
            curcol = 1


def _ComputeOffset(contents, line, col):
    curline = 1
    curcol = 1
    for i, byte in enumerate(contents):
        if (curline == line) and (curcol == col):
            return i
        curcol += 1
        if byte == "\n":
            curline += 1
            curcol = 1
    _logger.error("Dart completer - could not compute byte offset corresponding to L%i C%i", line,
                  col)
    return -1
