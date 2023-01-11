from os import path
from collections.abc import Iterable


class SettingsParser(object):
    def __init__(self, filepaths ='./settings.h'):
        self.files = filepaths if isinstance(filepaths, list) else [filepaths]
        self._defines = {}
        if self._read():
            self._recheck()
            self.impl()

    @property
    def defines(self):
        return self._defines

    def __setattr__(self, key, value):
        self.__dict__[key] = value
        #TODO подумать

    def __getattr__(self, item):
        return self.__dict__.get(item, None)
    """
    Это заглушка, чтобы редактор не ругался на отсутствующий аттрибут.
    Вообще я хз, чё делать. Объявить все нужные аттрибуты и заполнять их во время чтения? 
    Но тогда это будет очень много и негибко, т.к. в библиотеке они могут измениться, а ещё
    чем такой подход отличается от моего сейчас? Ведь в случае расхождений те аттрибуты, которые будут здесь, но которых
    не будет в библиотеке, всё так же будут типа None, как сейчас.
    """

    def impl(self):
        self.__dict__.update(self._defines)

    def _recheck(self):
        for k, v in {k:v for k, v in self._defines.items() if isinstance(v, str)}.items():
            if v in self._defines.keys():
                self._defines[k] = self._defines[v]
            else:
                self._defines.pop(k)


    def _read(self):
        for file in self.files:
            if path.exists(file):
                with open(file, 'r') as f:
                    separated = [l[8:].split()[:2] for l in f.readlines() if l.startswith("#define")]
                    self._defines.update(dict([el for el in separated if len(el) == 2]))
                for k, v in self._defines.items():
                    try:
                        self._defines[k] = int(v, 16 if '0x' in v else 10)
                    except:
                        # да, по-ёбнутому, но я хз как иначе
                        if self._defines[k] in {"true", "false"}:
                            self._defines[k] = True if self._defines[k] == "true" else False
        else:
            return True

    def save(self, filename = "declarations.py"):
        with open(filename, 'w') as f:
            f.writelines([f"{k} = {v}\n" for k, v in self._defines.items()])


