from pathlib import Path
from unittest.mock import (
    call,
    patch,
)
from urllib.parse import quote as urlquote

from datalad.tests.utils import (
    assert_equal,
    assert_in,
    assert_in_results,
    assert_raises,
    assert_result_count,
    assert_status,
    eq_,
    ok_,
)
# TODO find a replacement for this in anticipation of nose->pytest
from nose.tools import (
    assert_raises_regexp,
)

from datalad.api import (
    clone,
    create_sibling_webdav,
)
from datalad.distribution.dataset import (
    Dataset,
    require_dataset,
)
from datalad.support.exceptions import IncompleteResultsError
from datalad.tests.utils import (
    with_tempfile,
    with_tree
)
from datalad_next.tests.utils import (
    serve_path_via_webdav,
    with_credential,
)

from ..create_sibling_webdav import _get_url_credential


webdav_cred = ('dltest-my&=webdav', 'datalad', 'secure')


def test_common_workflow_implicit_cred():
    check_common_workflow(False, 'yes')


def test_common_workflow_explicit_cred():
    check_common_workflow(True, 'yes')


# to be used by https://github.com/datalad/datalad-next/pull/4
#def test_common_workflow_export():
#    check_common_workflow(False, 'export')


@with_credential(
    webdav_cred[0], user=webdav_cred[1], secret=webdav_cred[2],
    type='user_password')
@with_tempfile
@with_tempfile
@with_tempfile
@serve_path_via_webdav(auth=webdav_cred[1:])
def check_common_workflow(
        declare_credential, storage_sibling,
        clonepath, localpath, remotepath, url):
    ca = dict(result_renderer='disabled')
    ds = Dataset(localpath).create(**ca)
    # need to amend the test credential, can only do after we know the URL
    ds.credentials(
        'set',
        name=webdav_cred[0],
        # the test webdav webserver uses a realm label '/'
        spec=dict(realm=url + '/'),
        **ca)

    # we use a nasty target directory that has the potential to ruin the
    # git-remote URL handling
    targetdir_name = 'tar&get=mike'
    targetdir = Path(remotepath) / targetdir_name
    url = f'{url}/{targetdir_name}'

    res = ds.create_sibling_webdav(
        url,
        credential=webdav_cred[0] if declare_credential else None,
        storage_sibling=storage_sibling,
        **ca)
    assert_in_results(
        res,
        action='create_sibling_webdav.storage',
        status='ok',
        type='dataset',
        path=ds.path,
    )
    # where it should be accessible
    # needs to be quoted
    dlaurl = (
        'datalad-annex::?type=webdav&encryption=none&exporttree={exp}&'
        'url=http%3A//127.0.0.1%3A43612/tar%26get%3Dmike').format(
        exp='yes' if 'export' in storage_sibling else 'no',
    )
    if declare_credential:
        dlaurl += f'&dlacredential={urlquote(webdav_cred[0])}'

    assert_in_results(
        res,
        action='configure-sibling',
        status='ok',
        path=ds.path,
        name='127.0.0.1',
        url=dlaurl,
    )
    ok_(targetdir.exists())
    # add some annex payload
    (ds.pathobj / 'testfile.dat').write_text('dummy')
    ds.save(**ca)
    res = ds.push(to='127.0.0.1', **ca)
    assert_in_results(
        res,
        action='copy',
        path=str(ds.pathobj / 'testfile.dat'),
        status='ok',
    )
    assert_in_results(res, action='publish', status='ok')

    cloneurl = dlaurl
    if not declare_credential and 'export' in storage_sibling:
        # we can use a simplified URL
        cloneurl = 'webdav://{url}'.format(
            # strip http://
            url=url[7:],
        )
    dsclone = clone(cloneurl, clonepath, **ca)
    # we get the same thing
    eq_(ds.repo.get_hexsha(ds.repo.get_corresponding_branch()),
        dsclone.repo.get_hexsha(dsclone.repo.get_corresponding_branch()))

    # check that it auto-deploys webdav credentials
    # at some point, clone should be able to do this internally
    # https://github.com/datalad/datalad/issues/6634
    dsclone.siblings('enable', name='127.0.0.1-storage', **ca)
    # verify that we can get testfile.dat
    # just get the whole damn thing
    assert_status('ok', dsclone.get('.', **ca))
    # verify testfile content
    eq_('dummy', (dsclone.pathobj / 'testfile.dat').read_text())


def test_bad_url_catching():
    # Ensure that bad URLs are detected and handled

    check_pairs = [
        (
            "http://localhost:33322/abc?a",
            "URLs with query component are not supported:"
        ),
        (
            "this://netloc/has-a-fragment#sdsd",
            "URLs with fragment are not supported: {url!r}"
        ),
        (
            "this:has-no-net-location",
            "URLs without network location are not supported: {url!r}"
        ),
        (
            "xxx://localhost:33322/abc",
            "Only 'http'- or 'https'-scheme are supported: {url!r}"
        ),
    ]

    for bad_url, expected_message in check_pairs:
        assert_raises_regexp(
            ValueError,
            expected_message.format(url=bad_url),
            create_sibling_webdav,
            url=bad_url
        )


def test_http_warning():
    # Check that usage of http: triggers a warning.
    url = "http://localhost:33322/abc"

    with patch("datalad_next.create_sibling_webdav._get_url_credential") as gur_mock, \
         patch("datalad_next.create_sibling_webdav._create_sibling_webdav") as csw_mock, \
         patch("datalad_next.create_sibling_webdav.lgr") as lgr_mock:

        csw_mock.return_value = iter([])
        gur_mock.return_value = None

        # We set up the mocks to generate the following exception. This allows
        # us to limit the test to the logic in 'create_sibling_wabdav'.
        assert_raises_regexp(
            ValueError,
            f"No suitable credential for {url} found or specified",
            create_sibling_webdav,
            url=url)

        eq_(lgr_mock.warning.call_count, 1)
        assert_in(
            call(
                f"Using 'http:' ({url!r}) means that WebDAV credentials might "
                f"be sent unencrypted over network links. Consider using "
                f"'https:'."),
            lgr_mock.warning.mock_calls)


def test_constraints_checking():
    # Ensure that constraints are checked internally
    url = "http://localhost:22334/abc"
    for key in ("existing", "storage_sibling"):
        assert_raises_regexp(
            ValueError, "value is not one of",
            create_sibling_webdav,
            url=url,
            **{key: "illegal-value"})


def test_credential_handling():
    url = "https://localhost:22334/abc"
    with patch("datalad_next.create_sibling_webdav._get_url_credential") as gur_mock, \
         patch("datalad_next.create_sibling_webdav._create_sibling_webdav") as csw_mock, \
         patch("datalad_next.create_sibling_webdav.lgr") as lgr_mock:

        csw_mock.return_value = iter([])

        gur_mock.return_value = None
        assert_raises_regexp(
            ValueError,
            f"No suitable credential for {url} found or specified",
            create_sibling_webdav,
            url=url,
            name="some_name",
            existing="error")

        gur_mock.reset_mock()
        gur_mock.return_value = [None, {"some_key": "some_value"}]
        assert_raises_regexp(
            ValueError,
            f"No suitable credential for {url} found or specified",
            create_sibling_webdav,
            url=url,
            name="some_name",
            existing="error")

        # Ensure that failed credential storing is handled and logged
        gur_mock.reset_mock()
        gur_mock.return_value = [None, {"user": "u", "secret": "s"}]
        create_sibling_webdav(
            url=url,
            name="some_name",
            existing="error")


def test_name_clash_detection():
    # Ensure that constraints are checked internally
    url = "http://localhost:22334/abc"
    for storage_sibling in ("yes", 'export', 'only', 'only-export'):
        assert_raises_regexp(
            ValueError, "sibling names must not be equal",
            create_sibling_webdav,
            url=url,
            name="abc",
            storage_name="abc",
            storage_sibling=storage_sibling)


def test_unused_storage_name_warning():
    # Ensure that constraints are checked internally

    url = "https://localhost:22334/abc"

    with patch("datalad_next.create_sibling_webdav._get_url_credential") as gur_mock, \
         patch("datalad_next.create_sibling_webdav._create_sibling_webdav") as csw_mock, \
         patch("datalad_next.create_sibling_webdav.lgr") as lgr_mock:

        csw_mock.return_value = iter([])
        gur_mock.return_value = None

        storage_sibling_values = ("no", "only", "only-export")
        for storage_sibling in storage_sibling_values:
            # We set up the mocks to generate the following exception. This allows
            # us to limit the test to the logic in 'create_sibling_wabdav'.
            assert_raises(
                ValueError,
                create_sibling_webdav,
                url=url,
                name="abc",
                storage_name="abc",
                storage_sibling=storage_sibling)
        eq_(lgr_mock.warning.call_count, len(storage_sibling_values))


@with_tempfile
def test_check_existing_siblings(path):
    # Ensure that constraints are checked internally
    url = "http://localhost:22334/abc"

    ds = Dataset(path).create()

    with patch("datalad_next.create_sibling_webdav."
               "_yield_ds_w_matching_siblings") as ms_mock:

        ms_mock.return_value = [
            ("some_path", "some_name1"),
            ("some_path", "some_name2")]
        try:
            ds.create_sibling_webdav(
                url=url,
                name="some_name",
                existing="error")
        except IncompleteResultsError as ire:
            for existing_name in ("some_name1", "some_name2"):
                assert_in_results(
                    ire.failed,
                    action='create_sibling_webdav',
                    refds=ds.path,
                    status='error',
                    message=(
                            'a sibling %r is already configured in dataset %r',
                            existing_name,
                            'some_path')
                    )
        else:
            raise ValueError(
                "expected exception not raised: IncompleteResultsError")


def test_get_url_credential():
    url = "https://localhost:22334/abc"

    class MockCredentialManager:
        def __init__(self, name=None, credentials=None):
            self.name = name
            self.credentials = credentials

        def query(self, *args, **kwargs):
            if self.name or self.credentials:
                return [(self.name, kwargs.copy())]
            return None

        get = query

    with patch("datalad_next.create_sibling_webdav."
               "get_specialremote_credential_properties") as gscp_mock:

        # Expect credentials to be derived from WebDAV-url if no credential
        # name is provided
        gscp_mock.return_value = {"some": "value"}
        result = _get_url_credential(
            name=None,
            url=url,
            credman=MockCredentialManager("n1", "c1"))
        eq_(result, ("n1", {'_sortby': 'last-used', 'some': 'value'}))

        # Expect the credential name to be used, if provided
        result = _get_url_credential(
            name="some-name",
            url=url,
            credman=MockCredentialManager("x", "y"))
        eq_(result[0], "some-name")
        eq_(result[1][0][1]["name"], "some-name")

        # Expect the credentials to be derived from realm,
        # if no name is provided, and if the URL is not known.
        gscp_mock.reset_mock()
        gscp_mock.return_value = dict()
        result = _get_url_credential(
            name=None,
            url=url,
            credman=MockCredentialManager("u", "v"))
        eq_(result[0], None)
        eq_(result[1][0][1]["realm"], None)


@with_credential(
    'dltest-mywebdav', user=webdav_cred[1], secret=webdav_cred[2],
    type='user_password')
@with_tree(tree={'sub': {'f0': '0'},
                 'sub2': {'subsub': {'f1': '1'},
                          'f2': '2'},
                 'f3': '3'})
@with_tempfile
@serve_path_via_webdav(auth=webdav_cred[1:])
def test_existing_switch(localpath, remotepath, url):
    ca = dict(result_renderer='disabled')
    ds = Dataset(localpath).create(force=True, **ca)
    sub = ds.create('sub', force=True, **ca)
    sub2 = ds.create('sub2', force=True, **ca)
    subsub = sub2.create('subsub', force=True, **ca)
    ds.save(recursive=True)

    # need to amend the test credential, can only do after we know the URL
    ds.credentials(
        'set',
        name='dltest-mywebdav',
        # the test webdav webserver uses a realm label '/'
        spec=dict(realm=url + '/'),
        **ca)

    subsub.create_sibling_webdav(f'{url}/sub2/subsub', storage_sibling='yes',
                                 **ca)
    sub2.create_sibling_webdav(f'{url}/sub2', storage_sibling='only', **ca)
    sub.create_sibling_webdav(f'{url}/sub', storage_sibling='no', **ca)

    res = ds.create_sibling_webdav(f'{url}', storage_sibling='yes',
                                   existing='skip',
                                   recursive=True, **ca)
    dlaurl='datalad-annex::?type=webdav&encryption=none&exporttree=no&' \
           'url=http%3A//127.0.0.1%3A43612/'

    # results per dataset:
    # super:
    assert_in_results(
        res,
        action='create_sibling_webdav.storage',
        status='ok',
        type='dataset',
        path=ds.path
    )
    assert_in_results(
        res,
        action='add-sibling',
        status='ok',
        type='sibling',
        path=ds.path,
        name='127.0.0.1',
        url=dlaurl[:-1],
    )
    # sub
    assert_in_results(
        res,
        action='create_sibling_webdav.storage',
        status='ok',
        type='dataset',
        path=sub.path
    )
    assert_in_results(
        res,
        action='create_sibling_webdav',
        status='notneeded',
        type='dataset',
        path=sub.path,
    )
    # sub2
    assert_in_results(
        res,
        action='create_sibling_webdav',
        status='notneeded',
        type='dataset',
        path=sub2.path
    )
    assert_in_results(
        res,
        action='add-sibling',
        status='ok',
        type='sibling',
        path=sub2.path,
        name='127.0.0.1',
        url=dlaurl + 'sub2'
    )
    # subsub
    assert_in_results(
        res,
        action='create_sibling_webdav',
        status='notneeded',
        type='dataset',
        path=subsub.path
    )
    assert_in_results(
        res,
        action='create_sibling_webdav',
        status='notneeded',
        type='dataset',
        path=subsub.path,
    )

    # should fail upfront with first discovered remote that already exist
    assert_raises(IncompleteResultsError, ds.create_sibling_webdav, f'{url}',
                  storage_sibling='yes', existing='error', recursive=True, **ca)

    srv_rt = Path(remotepath)
    (srv_rt / 'sub').rmdir()
    (srv_rt / 'sub2' / 'subsub').rmdir()
    (srv_rt / 'sub2').rmdir()

    # existing=skip actually doesn't do anything (other than yielding notneeded)
    res = ds.create_sibling_webdav(f'{url}', storage_sibling='yes',
                                   existing='skip',
                                   recursive=True, **ca)
    assert_result_count(res, 8, status='notneeded')
    remote_content = list(srv_rt.glob('**'))
    assert_equal(len(remote_content), 1)  # nothing but root dir

    # reconfigure to move target one directory level:
    dlaurl += 'reconfigure'
    url += '/reconfigure'
    new_root = srv_rt / 'reconfigure'
    res = ds.create_sibling_webdav(f'{url}', storage_sibling='yes',
                                   existing='reconfigure',
                                   recursive=True, **ca)
    assert_result_count(res, 8, status='ok')
    remote_content = list(new_root.glob('**'))
    assert_in(new_root / 'sub', remote_content)
    assert_in(new_root / 'sub2', remote_content)
    assert_in(new_root / 'sub2' / 'subsub', remote_content)
