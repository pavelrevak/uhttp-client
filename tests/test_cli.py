#!/usr/bin/env python3
"""Tests for CLI module"""

import unittest
import sys
import io
from unittest.mock import patch, MagicMock

from uhttp.cli import parse_headers, format_size, HTTP_METHODS, main


class TestParseHeaders(unittest.TestCase):
    """Test header parsing"""

    def test_empty(self):
        """Test empty header list"""
        self.assertEqual(parse_headers(None), {})
        self.assertEqual(parse_headers([]), {})

    def test_single_header(self):
        """Test single header"""
        result = parse_headers(['Content-Type: application/json'])
        self.assertEqual(result, {'Content-Type': 'application/json'})

    def test_multiple_headers(self):
        """Test multiple headers"""
        result = parse_headers([
            'Content-Type: application/json',
            'Authorization: Bearer token123'
        ])
        self.assertEqual(result, {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer token123'
        })

    def test_header_with_extra_colons(self):
        """Test header value containing colons"""
        result = parse_headers(['X-Custom: value:with:colons'])
        self.assertEqual(result, {'X-Custom': 'value:with:colons'})

    def test_header_whitespace_stripped(self):
        """Test whitespace is stripped"""
        result = parse_headers(['  Key  :  Value  '])
        self.assertEqual(result, {'Key': 'Value'})

    def test_header_without_colon_ignored(self):
        """Test header without colon is ignored"""
        result = parse_headers(['InvalidHeader', 'Valid: Header'])
        self.assertEqual(result, {'Valid': 'Header'})


class TestFormatSize(unittest.TestCase):
    """Test size formatting"""

    def test_bytes(self):
        """Test bytes formatting"""
        self.assertEqual(format_size(0), '0 B')
        self.assertEqual(format_size(100), '100 B')
        self.assertEqual(format_size(1023), '1023 B')

    def test_kilobytes(self):
        """Test kilobytes formatting"""
        self.assertEqual(format_size(1024), '1.0 KB')
        self.assertEqual(format_size(1536), '1.5 KB')
        self.assertEqual(format_size(10240), '10.0 KB')

    def test_megabytes(self):
        """Test megabytes formatting"""
        self.assertEqual(format_size(1024 * 1024), '1.0 MB')
        self.assertEqual(format_size(1024 * 1024 * 5), '5.0 MB')
        self.assertEqual(format_size(1024 * 1024 + 512 * 1024), '1.5 MB')


class TestHTTPMethods(unittest.TestCase):
    """Test HTTP methods constant"""

    def test_all_methods_present(self):
        """Test all standard methods are present"""
        self.assertIn('GET', HTTP_METHODS)
        self.assertIn('POST', HTTP_METHODS)
        self.assertIn('PUT', HTTP_METHODS)
        self.assertIn('DELETE', HTTP_METHODS)
        self.assertIn('PATCH', HTTP_METHODS)
        self.assertIn('HEAD', HTTP_METHODS)
        self.assertIn('OPTIONS', HTTP_METHODS)


class TestCLIArgumentParsing(unittest.TestCase):
    """Test CLI argument parsing"""

    def run_cli(self, args, mock_client=None):
        """Helper to run CLI with mocked client"""
        if mock_client is None:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.status_message = 'OK'
            mock_response.headers = {}
            mock_response.data = b'{"result": "ok"}'
            mock_client.request.return_value.wait.return_value = mock_response

        with patch('uhttp.cli._client.HttpClient', return_value=mock_client):
            with patch('uhttp.cli._client.parse_url') as mock_parse:
                mock_parse.return_value = ('example.com', 80, '/path', False, None)
                with patch('sys.argv', ['uhttp'] + args):
                    with patch('sys.stdout', new_callable=io.StringIO):
                        with patch('sys.stderr', new_callable=io.StringIO):
                            try:
                                main()
                            except SystemExit as e:
                                if e.code not in (0, None):
                                    raise
        return mock_client

    def test_url_only_get(self):
        """Test URL only defaults to GET"""
        mock = self.run_cli(['http://example.com/path'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'GET')

    def test_explicit_get(self):
        """Test explicit GET method"""
        mock = self.run_cli(['GET', 'http://example.com/path'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'GET')

    def test_explicit_post(self):
        """Test explicit POST method"""
        mock = self.run_cli(['POST', 'http://example.com/path'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'POST')

    def test_explicit_put(self):
        """Test explicit PUT method"""
        mock = self.run_cli(['PUT', 'http://example.com/path', '-d', 'data'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'PUT')

    def test_explicit_delete(self):
        """Test explicit DELETE method"""
        mock = self.run_cli(['DELETE', 'http://example.com/path'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'DELETE')

    def test_explicit_patch(self):
        """Test explicit PATCH method"""
        mock = self.run_cli(['PATCH', 'http://example.com/path', '-d', 'data'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'PATCH')

    def test_data_implies_post(self):
        """Test -d data implies POST method"""
        mock = self.run_cli(['http://example.com/path', '-d', 'key=value'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'POST')

    def test_json_implies_post(self):
        """Test -j json implies POST method"""
        mock = self.run_cli(['http://example.com/path', '-j', '{"key": "value"}'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'POST')

    def test_explicit_method_overrides_data(self):
        """Test explicit method is used even with data"""
        mock = self.run_cli(['PUT', 'http://example.com/path', '-d', 'data'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'PUT')

    def test_lowercase_method(self):
        """Test lowercase method is uppercased"""
        mock = self.run_cli(['get', 'http://example.com/path'])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        self.assertEqual(call_args[0][0], 'GET')

    def test_unknown_method_error(self):
        """Test unknown method raises error"""
        with self.assertRaises(SystemExit):
            with patch('sys.stderr', new_callable=io.StringIO):
                self.run_cli(['UNKNOWN', 'http://example.com/path'])

    def test_url_without_protocol(self):
        """Test URL without protocol gets http:// added"""
        with patch('uhttp.cli._client.HttpClient') as mock_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.data = b'{}'
            mock_client.request.return_value.wait.return_value = mock_response
            mock_class.return_value = mock_client

            with patch('uhttp.cli._client.parse_url') as mock_parse:
                mock_parse.return_value = ('example.com', 80, '/', False, None)
                with patch('sys.argv', ['uhttp', 'example.com']):
                    with patch('sys.stdout', new_callable=io.StringIO):
                        main()
                # parse_url should receive URL with protocol
                mock_parse.assert_called_with('http://example.com')

    def test_custom_headers(self):
        """Test custom headers are passed"""
        mock = self.run_cli([
            'http://example.com/path',
            '-H', 'X-Custom: value1',
            '-H', 'Authorization: Bearer token'
        ])
        mock.request.assert_called_once()
        call_args = mock.request.call_args
        headers = call_args[1].get('headers', {})
        self.assertEqual(headers.get('X-Custom'), 'value1')
        self.assertEqual(headers.get('Authorization'), 'Bearer token')


class TestCLIErrors(unittest.TestCase):
    """Test CLI error handling"""

    def test_no_arguments(self):
        """Test no arguments shows error"""
        with patch('sys.argv', ['uhttp']):
            with patch('sys.stderr', new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as ctx:
                    main()
                self.assertNotEqual(ctx.exception.code, 0)

    def test_invalid_json(self):
        """Test invalid JSON shows error"""
        with patch('sys.argv', ['uhttp', 'http://example.com', '-j', 'not json']):
            with patch('sys.stderr', new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as ctx:
                    main()
                self.assertEqual(ctx.exception.code, 1)

    def test_too_many_arguments(self):
        """Test too many positional arguments shows error"""
        with patch('sys.argv', ['uhttp', 'GET', 'http://example.com', 'extra']):
            with patch('sys.stderr', new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as ctx:
                    main()
                self.assertNotEqual(ctx.exception.code, 0)


if __name__ == '__main__':
    unittest.main()
