class TrString(str):

    def __new__(cls, msgid, domain=None, context=None,
                modarg=None, fmtarg=None):
        self = str.__new__(cls, msgid)

        if isinstance(msgid, self.__class__):
            domain = domain or msgid.domain and msgid.domain[:]
            context = context or msgid.context and msgid.context[:]
            fmtarg = fmtarg or msgid.fmtarg and msgid.fmtarg[:]
            modarg = (modarg if modarg is not None else msgid.modarg
                      and msgid.modarg[:])

        self.domain = domain
        self.context = context
        self.modarg = modarg
        self.fmtarg = fmtarg
        return self

    def __mod__(self, argument):
        return self.__class__(self, modarg=argument)


def trstring_factory(domain):
    def create(msgid, **kwargs):
        return TrString(msgid, domain=domain, **kwargs)
    return create
