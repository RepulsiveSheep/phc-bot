import os

import praw.models
import yaml

from phc_bot.app import clean_ph_links, get_string_to_search, get_ph_title, escape_reddit_link_text, \
    get_image_urls_for_submission


class TestCleanPhLinks:

    def test_empty(self):
        assert clean_ph_links([]) == ()
        assert clean_ph_links(()) == ()

    def test_some_ph_links(self):
        in_links = [
            'https://google.com/',
            'https://xy.pornhub.com/view_video.php?viewkey=dummy',
            'https://random.link.test/hahahaha',
            'https://www.pornhub.com/abcd',
            'https://es.pornhub.com/xyz',
            'https://pornhub.com/foobar',
        ]
        out_links = (
            'https://www.pornhub.com/view_video.php?viewkey=dummy',
            'https://www.pornhub.com/abcd',
            'https://www.pornhub.com/xyz',
            'https://www.pornhub.com/foobar',
        )
        assert clean_ph_links(in_links) == out_links

    def test_all_ph_links(self):
        in_links = [
            'https://xy.pornhub.com/view_video.php?viewkey=dummy',
            'https://pornhub.com/foobar',
            'https://www.pornhub.com/abcd',
            'https://es.pornhub.com/xyz',
        ]
        out_links = (
            'https://www.pornhub.com/view_video.php?viewkey=dummy',
            'https://www.pornhub.com/foobar',
            'https://www.pornhub.com/abcd',
            'https://www.pornhub.com/xyz',
        )
        assert clean_ph_links(in_links) == out_links

    def test_no_ph_links(self):
        in_links = [
            'https://google.com/',
            'https://random.link.test/hahahaha',
        ]
        assert clean_ph_links(in_links) == ()


class TestGetStringToSearch:

    def test_empty(self):
        assert get_string_to_search('') == ''

    def test_strip(self):
        assert get_string_to_search('   hello world   ') == 'hello world'

    def test_samples(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, 'samples.yaml')) as f:
            samples = yaml.full_load(f)['samples']
            for sample in samples:
                in_text = sample['input']
                out_text = sample['output']
                assert get_string_to_search(in_text) == get_string_to_search(out_text)


SAMPLE_URL = 'https://example.com'


class TestGetPhTitle:

    def test_missing_title(self, requests_mock):
        requests_mock.get(SAMPLE_URL, text='')
        assert get_ph_title(SAMPLE_URL) is None
        requests_mock.get(SAMPLE_URL, text='<!DOCTYPE html><html lang="en"><body>no title lol</body></html>')
        assert get_ph_title(SAMPLE_URL) is None

    def test_normal_title(self, requests_mock):
        title = 'Some title - haha.com'
        requests_mock.get(SAMPLE_URL, text=f'<title>{title}</title>')
        assert get_ph_title(SAMPLE_URL) == title
        title = 'Another title - lol.com'
        requests_mock.get(SAMPLE_URL,
                          text=f'<!DOCTYPE html><html><head>\n\n    <title>{title}</title>\n\n</head><body>hello'
                               f'</body></html>')
        assert get_ph_title(SAMPLE_URL) == title

    def test_empty_title(self, requests_mock):
        requests_mock.get(SAMPLE_URL, text=f'<title></title>')
        assert get_ph_title(SAMPLE_URL) is None
        requests_mock.get(SAMPLE_URL,
                          text=f'<!DOCTYPE html><html><head><title></title></head><body>hello</body></html>')
        assert get_ph_title(SAMPLE_URL) is None


class TestEscapeRedditLinkTest:

    def test_empty(self):
        assert escape_reddit_link_text('') == ''

    def test_square_brackets(self):
        assert escape_reddit_link_text(r'Hello, [this] is some [text]') == r'Hello, \[this\] is some \[text\]'

    def test_asterisk(self):
        assert escape_reddit_link_text(r'Keep **this** in *mind*') == r'Keep \*\*this\*\* in \*mind\*'

    def test_underscore(self):
        assert escape_reddit_link_text(r'_Great_ job, _keep it up_') == r'\_Great\_ job, \_keep it up\_'

    def test_mixed(self):
        assert escape_reddit_link_text(
            r'_*Great*_ [job], *_keep it up*_') == r'\_\*Great\*\_ \[job\], \*\_keep it up\*\_'


class TestGetImageUrlsFromSubmission:

    def test_reddit_gallery(self):
        submission = praw.models.Submission(get_reddit())
        assert get_image_urls_for_submission()
