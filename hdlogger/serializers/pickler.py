from dill import _Pickler as dillPickler, Unpickler as dillUnpickler
from pickle import _Pickler as picklePickler, Unpickler as pickleUnpickler


### DILL: Extend the Picklers
class Pickler(StockPickler):
    """python's Pickler extended to interpreter sessions"""
    dispatch = MetaCatchingDict(StockPickler.dispatch.copy())
    _session = False
    from .settings import settings

    def __init__(self, *args, **kwds):
        settings = Pickler.settings
        _byref = kwds.pop('byref', None)
       #_strictio = kwds.pop('strictio', None)
        _fmode = kwds.pop('fmode', None)
        _recurse = kwds.pop('recurse', None)
        StockPickler.__init__(self, *args, **kwds)
        self._main = _main_module
        self._diff_cache = {}
        self._byref = settings['byref'] if _byref is None else _byref
        self._strictio = False #_strictio
        self._fmode = settings['fmode'] if _fmode is None else _fmode
        self._recurse = settings['recurse'] if _recurse is None else _recurse

    def dump(self, obj): #NOTE: if settings change, need to update attributes
        stack.clear()  # clear record of 'recursion-sensitive' pickled objects
        # register if the object is a numpy ufunc
        # thanks to Paul Kienzle for pointing out ufuncs didn't pickle
        if NumpyUfuncType and numpyufunc(obj):
            @register(type(obj))
            def save_numpy_ufunc(pickler, obj):
                log.info("Nu: %s" % obj)
                StockPickler.save_global(pickler, obj)
                log.info("# Nu")
                return
            # NOTE: the above 'save' performs like:
            #   import copy_reg
            #   def udump(f): return f.__name__
            #   def uload(name): return getattr(numpy, name)
            #   copy_reg.pickle(NumpyUfuncType, udump, uload)
        # register if the object is a subclassed numpy array instance
        if NumpyArrayType and ndarraysubclassinstance(obj):
            @register(type(obj))
            def save_numpy_array(pickler, obj):
                log.info("Nu: (%s, %s)" % (obj.shape,obj.dtype))
                npdict = getattr(obj, '__dict__', None)
                f, args, state = obj.__reduce__()
                pickler.save_reduce(_create_array, (f,args,state,npdict), obj=obj)
                log.info("# Nu")
                return
        # end hack
        if GENERATOR_FAIL and type(obj) == GeneratorType:
            msg = "Can't pickle %s: attribute lookup builtins.generator failed" % GeneratorType
            raise PicklingError(msg)
        else:
            StockPickler.dump(self, obj)
        stack.clear()  # clear record of 'recursion-sensitive' pickled objects
        return
    dump.__doc__ = StockPickler.dump.__doc__
    pass

class Unpickler(StockUnpickler):
    """python's Unpickler extended to interpreter sessions and more types"""
    from .settings import settings
    _session = False

    def find_class(self, module, name):
        if (module, name) == ('__builtin__', '__main__'):
            return self._main.__dict__ #XXX: above set w/save_module_dict
        elif (module, name) == ('__builtin__', 'NoneType'):
            return type(None) #XXX: special case: NoneType missing
        if module == 'dill.dill': module = 'dill._dill'
        return StockUnpickler.find_class(self, module, name)

    def __init__(self, *args, **kwds):
        settings = Pickler.settings
        _ignore = kwds.pop('ignore', None)
        StockUnpickler.__init__(self, *args, **kwds)
        self._main = _main_module
        self._ignore = settings['ignore'] if _ignore is None else _ignore

    def load(self): #NOTE: if settings change, need to update attributes
        obj = StockUnpickler.load(self)
        if type(obj).__module__ == getattr(_main_module, '__name__', '__main__'):
            if not self._ignore:
                # point obj class to main
                try: obj.__class__ = getattr(self._main, type(obj).__name__)
                except (AttributeError,TypeError): pass # defined in a file
       #_main_module.__dict__.update(obj.__dict__) #XXX: should update globals ?
        return obj
    load.__doc__ = StockUnpickler.load.__doc__
    pass


class Pickler(
