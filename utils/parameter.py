def parameter_check(js, fields):
    for f, t in fields.items():
        t1 = type(js.get(f))
        if js.get(f) is None or t1 != t if type(t) != list else t1 not in t:
            raise RuntimeError('bad parameter %s' % f)
