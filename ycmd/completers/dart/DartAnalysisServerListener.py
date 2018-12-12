# AUTOGENERATED FILE - DO NOT MODIFY!
# This file generated by Djinni from dart-as.djinni

from djinni.support import MultiSet # default imported in all files
from djinni.exception import CPyException # default imported in all files
from djinni.pycffi_marshal import CPyPrimitive, CPyString

from abc import ABCMeta, abstractmethod
from future.utils import with_metaclass
from PyCFFIlib_cffi import ffi, lib

from djinni import exception # this forces run of __init__.py which gives cpp option to call back into py to create exception

class DartAnalysisServerListener(with_metaclass(ABCMeta)):
    @abstractmethod
    def on_server_ready(self, version, pid):
        raise NotImplementedError

    @abstractmethod
    def on_server_error(self, error_str):
        raise NotImplementedError

    @abstractmethod
    def on_response_available(self, response_str):
        raise NotImplementedError


class DartAnalysisServerListenerCallbacksHelper():
    @ffi.callback("void(struct DjinniObjectHandle * , struct DjinniString *, int64_t)")
    def on_server_ready(cself, version, pid):
        try:
            DartAnalysisServerListenerHelper.selfToPy(cself).on_server_ready(CPyString.toPy(version), CPyPrimitive.toPy(pid))
        except Exception as _djinni_py_e:
            CPyException.setExceptionFromPy(_djinni_py_e)

    @ffi.callback("void(struct DjinniObjectHandle * , struct DjinniString *)")
    def on_server_error(cself, error_str):
        try:
            DartAnalysisServerListenerHelper.selfToPy(cself).on_server_error(CPyString.toPy(error_str))
        except Exception as _djinni_py_e:
            CPyException.setExceptionFromPy(_djinni_py_e)

    @ffi.callback("void(struct DjinniObjectHandle * , struct DjinniString *)")
    def on_response_available(cself, response_str):
        try:
            DartAnalysisServerListenerHelper.selfToPy(cself).on_response_available(CPyString.toPy(response_str))
        except Exception as _djinni_py_e:
            CPyException.setExceptionFromPy(_djinni_py_e)

    @ffi.callback("void(struct DjinniObjectHandle * )")
    def __delete(c_ptr):
        assert c_ptr in DartAnalysisServerListenerHelper.c_data_set
        DartAnalysisServerListenerHelper.c_data_set.remove(c_ptr)

    @staticmethod
    def _add_callbacks():
        lib.DartAnalysisServerListener_add_callback_on_server_ready(DartAnalysisServerListenerCallbacksHelper.on_server_ready)
        lib.DartAnalysisServerListener_add_callback_on_server_error(DartAnalysisServerListenerCallbacksHelper.on_server_error)
        lib.DartAnalysisServerListener_add_callback_on_response_available(DartAnalysisServerListenerCallbacksHelper.on_response_available)

        lib.DartAnalysisServerListener_add_callback___delete(DartAnalysisServerListenerCallbacksHelper.__delete)

DartAnalysisServerListenerCallbacksHelper._add_callbacks()

class DartAnalysisServerListenerHelper:
    c_data_set = MultiSet()
    @staticmethod
    def toPy(obj):
        if obj == ffi.NULL:
            return None
        # Python Objects can be returned without being wrapped in proxies
        py_handle = lib.get_handle_from_proxy_object_cw__DartAnalysisServerListener(obj)
        if py_handle:
            assert py_handle in DartAnalysisServerListenerHelper.c_data_set
            aux = ffi.from_handle(ffi.cast("void * ", py_handle))
            lib.DartAnalysisServerListener___wrapper_dec_ref(obj)
            return aux
        return DartAnalysisServerListenerCppProxy(obj)

    @staticmethod
    def selfToPy(obj):
        assert obj in DartAnalysisServerListenerHelper.c_data_set
        return ffi.from_handle(ffi.cast("void * ",obj))

    @staticmethod
    def fromPy(py_obj):
        if py_obj is None:
            return ffi.NULL
        py_proxy = (py_obj)
        if not hasattr(py_obj, "on_server_ready"):
            raise TypeError
        if not hasattr(py_obj, "on_server_error"):
            raise TypeError
        if not hasattr(py_obj, "on_response_available"):
            raise TypeError

        bare_c_ptr = ffi.new_handle(py_proxy)
        DartAnalysisServerListenerHelper.c_data_set.add(bare_c_ptr)
        wrapped_c_ptr = lib.make_proxy_object_from_handle_cw__DartAnalysisServerListener(bare_c_ptr)
        return wrapped_c_ptr
