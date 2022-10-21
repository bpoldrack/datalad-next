import pathlib
import pytest

from ..basic import (
    EnsureInt,
    EnsureFloat,
    EnsureBool,
    EnsureStr,
    EnsureStrPrefix,
    EnsureNone,
    EnsureCallable,
    EnsureChoice,
    EnsureKeyChoice,
    EnsureMapping,
    EnsureRange,
    EnsureIterableOf,
    EnsureListOf,
    EnsureTupleOf,
    EnsurePath,
    EnsureValue,
    NoConstraint,
)
from ..utils import _type_str


def test_noconstraint():
    c = NoConstraint()
    assert c(5) == 5
    assert c.short_description() == ''


def test_int():
    c = EnsureInt()
    # this should always work
    assert c(7) == 7
    assert c(7.0) == 7
    assert c('7') == 7
    # no automatic inspection of iterables, should use EnsureIterableOf
    with pytest.raises(TypeError):
        c([7, 3])
    # this should always fail
    with pytest.raises(ValueError):
        c('fail')
    # this will also fail
    with pytest.raises(ValueError):
        c('17.0')
    assert c.short_description() == 'int'


def test_float():
    c = EnsureFloat()
    # this should always work
    assert c(7.0) == 7.0
    assert c(7) == 7.0
    assert c('7') == 7.0
    # no automatic inspection of iterables, should use EnsureIterableOf
    with pytest.raises(TypeError):
        c([7.0, '3.0'])
    # this should always fail
    with pytest.raises(ValueError):
        c('fail')


def test_bool():
    c = EnsureBool()
    # this should always work
    assert c(True) is True
    assert c(False) is False
    # all that resuls in True
    assert c('True') is True
    assert c('true') is True
    assert c('1') is True
    assert c('yes') is True
    assert c('on') is True
    assert c('enable') is True
    # all that resuls in False
    assert c('false') is False
    assert c('False') is False
    assert c('0') is False
    assert c('no') is False
    assert c('off') is False
    assert c('disable') is False
    # this should always fail
    with pytest.raises(ValueError):
        c(0)
    with pytest.raises(ValueError):
        c(1)


def test_str():
    c = EnsureStr()
    # this should always work
    assert c('hello') == 'hello'
    assert c('7.0') == '7.0'
    # this should always fail
    with pytest.raises(ValueError):
        c(['ab'])
    with pytest.raises(ValueError):
        c(['a', 'b'])
    with pytest.raises(ValueError):
        c(('a', 'b'))
    # no automatic conversion attempted
    with pytest.raises(ValueError):
        c(7.0)
    assert c.short_description() == 'str'


def test_str_min_len():
    c = EnsureStr(min_len=1)
    assert c('hello') == 'hello'
    assert c('h') == 'h'
    with pytest.raises(ValueError):
        c('')

    c = EnsureStr(min_len=2)
    assert c('hello') == 'hello'
    with pytest.raises(ValueError):
        c('h')


def test_EnsureStr_match():
    # alphanum plus _ and ., non-empty
    pattern = '[a-zA-Z0-9-.]+'
    constraint = EnsureStr(match=pattern)

    # reports the pattern in the description
    for m in (constraint.short_description, constraint.long_description):
        assert pattern in m()

    # must work
    assert constraint('a0F-2.') == 'a0F-2.'

    for v in ('', '123_abc'):
        with pytest.raises(ValueError):
            assert constraint('')


def test_EnsureStrPrefix():
    c = EnsureStrPrefix('some-')
    c('some-mess') == 'some-mess'
    with pytest.raises(ValueError):
        c('mess')
    assert c.short_description() == 'some-...'
    assert c.long_description() == "value must start with 'some-'"


def test_EnsureValue():
    c = EnsureValue(5)
    assert c.short_description() == '5'
    # this should always work
    assert c(5) == 5
    # type mismatch
    with pytest.raises(ValueError):
        c('5')
    # value mismatches
    with pytest.raises(ValueError):
        c('None')
    with pytest.raises(ValueError):
        c([])


# special case of EnsureValue
def test_none():
    c = EnsureNone()
    assert c.short_description() == 'None'
    # this should always work
    assert c(None) is None
    # this should always fail
    with pytest.raises(ValueError):
        c('None')
    with pytest.raises(ValueError):
        c([])


def test_callable():
    c = EnsureCallable()
    assert c.short_description() == 'callable'
    assert c.long_description() == 'value must be a callable'
    # this should always work
    assert c(range) == range
    with pytest.raises(ValueError):
        c('range')


def test_choice():
    c = EnsureChoice('choice1', 'choice2', None)
    descr = c.long_description()
    for i in ('choice1', 'choice2', 'CMD', 'PY'):
        assert i in descr
    # short is a "set" or repr()s
    assert c.short_description() == "{'choice1', 'choice2', None}"
    # this should always work
    assert c('choice1') == 'choice1'
    assert c(None) is None
    # this should always fail
    with pytest.raises(ValueError):
        c('fail')
    with pytest.raises(ValueError):
        c('None')


def test_keychoice():
    c = EnsureKeyChoice(key='some', values=('choice1', 'choice2', None))
    descr = c.long_description()
    for i in ('some', 'choice1', 'choice2'):
        assert i in descr
    assert c.short_description() == "some:{'choice1', 'choice2', None}"
    assert c({'some': 'choice1'}) == {'some': 'choice1'}
    assert c({'some': None}) == {'some': None}
    assert c({'some': None, 'ign': 'ore'}) == {'some': None, 'ign': 'ore'}
    with pytest.raises(ValueError):
        c('fail')
    with pytest.raises(ValueError):
        c('None')
    with pytest.raises(ValueError):
        c({'nope': 'None'})
    with pytest.raises(ValueError):
        c({'some': 'None'})
    with pytest.raises(ValueError):
        c({'some': ('a', 'b')})


def test_range():
    with pytest.raises(ValueError):
        EnsureRange(min=None, max=None)
    c = EnsureRange(max=7)
    assert c.short_description() == 'not greater than 7'
    c = EnsureRange(min=3, max=7)
    # this should always work
    assert c(3.0) == 3.0

    # this should always fail
    with pytest.raises(ValueError):
        c(2.9999999)
    with pytest.raises(ValueError):
        c(77)
    with pytest.raises(TypeError):
        c('fail')
    with pytest.raises(TypeError):
        c((3, 4))
    # since no type checks are performed
    with pytest.raises(TypeError):
        c('7')

    # Range doesn't have to be numeric
    c = EnsureRange(min="e", max="qqq")
    assert c('e') == 'e'
    assert c('fa') == 'fa'
    assert c('qq') == 'qq'
    with pytest.raises(ValueError):
        c('a')
    with pytest.raises(ValueError):
        c('qqqa')


# imported from ancient test code in datalad-core,
# main test is test_EnsureIterableOf
def test_EnsureTupleOf():
    c = EnsureTupleOf(str)
    assert c(['a', 'b']) == ('a', 'b')
    assert c(['a1', 'b2']) == ('a1', 'b2')
    assert c.short_description() == "tuple(<class 'str'>)"


# imported from ancient test code in datalad-core,
# main test is test_EnsureIterableOf
def test_EnsureListOf():
    c = EnsureListOf(str)
    assert c(['a', 'b']) == ['a', 'b']
    assert c(['a1', 'b2']) == ['a1', 'b2']
    assert c.short_description() == "list(<class 'str'>)"


def test_EnsureIterableOf():
    c = EnsureIterableOf(list, int)
    assert c.short_description() == "<class 'list'>(<class 'int'>)"
    assert c.item_constraint == int
    # testing aspects that are not covered by test_EnsureListOf
    tgt = [True, False, True]
    assert EnsureIterableOf(list, bool)((1, 0, 1)) == tgt
    assert EnsureIterableOf(list, bool, min_len=3, max_len=3)((1, 0, 1)) == tgt
    with pytest.raises(ValueError):
        # too many items
        EnsureIterableOf(list, bool, max_len=2)((1, 0, 1))
    with pytest.raises(ValueError):
        # too few items
        EnsureIterableOf(list, bool, min_len=4)((1, 0, 1))
    with pytest.raises(ValueError):
        # invalid specification min>max
        EnsureIterableOf(list, bool, min_len=1, max_len=0)
    with pytest.raises(TypeError):
        # item_constraint fails
        EnsureIterableOf(list, dict)([5.6, 3.2])
    with pytest.raises(ValueError):
        # item_constraint fails
        EnsureIterableOf(list, EnsureBool())([5.6, 3.2])

    seq = [3.3, 1, 2.6]

    def _mygen():
        for i in seq:
            yield i

    def _myiter(iter):
        for i in iter:
            yield i

    # feeding a generator into EnsureIterableOf and getting one out
    assert list(EnsureIterableOf(_myiter, int)(_mygen())) == [3, 1, 2]


def test_type_str():
    assert _type_str((str,)) == 'str'
    assert _type_str(str) == 'str'


def test_EnsurePath(tmp_path):
    target = pathlib.Path(tmp_path)

    assert EnsurePath()(tmp_path) == target
    assert EnsurePath(lexists=True)(tmp_path) == target
    with pytest.raises(ValueError):
        EnsurePath(lexists=False)(tmp_path)
    with pytest.raises(ValueError):
        EnsurePath(lexists=True)(tmp_path / 'nothere')
    assert EnsurePath(is_format='absolute')(tmp_path) == target
    with pytest.raises(ValueError):
        EnsurePath(is_format='relative')(tmp_path)
    with pytest.raises(ValueError):
        EnsurePath(is_format='absolute')(tmp_path.name)
    from stat import S_ISDIR, S_ISREG
    assert EnsurePath(is_mode=S_ISDIR)(tmp_path) == target
    with pytest.raises(ValueError):
        EnsurePath(is_mode=S_ISREG)(tmp_path)
    # give particular path type
    assert EnsurePath(path_type=pathlib.PurePath
        )(tmp_path) == pathlib.PurePath(tmp_path)
    # not everything is possible, this is known and OK
    with pytest.raises(AttributeError):
        EnsurePath(
            path_type=pathlib.PurePath,
            is_mode=S_ISREG,
        )(tmp_path)
    assert EnsurePath().short_description() == 'path'
    assert EnsurePath(is_format='absolute').short_description() == 'absolute path'
    # default comparison mode is parent-or-same-as
    c = EnsurePath(ref=target)
    assert c(target) == target
    assert c(target / 'some') == target / 'some'
    with pytest.raises(ValueError):
        assert c(target.parent)
    c = EnsurePath(ref=target, ref_is='parent-of')
    assert c(target / 'some') == target / 'some'
    with pytest.raises(ValueError):
        assert c(target)
    assert c.short_description() == f'path that is parent-of {target}'
    c = EnsurePath(ref=target, ref_is='stupid')
    with pytest.raises(ValueError):
        c('doesnotmatter')


def test_EnsureMapping():
    true_key = 5
    true_value = False

    constraint = EnsureMapping(EnsureInt(), EnsureBool(), delimiter='::')
    # called without a mapping type
    with pytest.raises(ValueError):
        constraint(true_key)

    assert 'mapping of int -> bool' in constraint.short_description()

    # must all work
    for v in ('5::no',
              [5, 'false'],
              ('5', False),
              {'5': 'False'},
    ):
        d = constraint(v)
        assert isinstance(d, dict)
        assert len(d) == 1
        k, v = d.popitem()
        assert k == true_key
        assert v == true_value

    # must all fail
    for v in ('5',
              [],
              tuple(),
              {},
              # additional value
              [5, False, False],
              {'5': 'False', '6': True}):
        with pytest.raises(ValueError):
            d = constraint(v)

    # TODO test for_dataset() once we have a simple EnsurePathInDataset
