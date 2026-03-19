#!/usr/bin/env python3
"""
Integration tests with real HTTP/HTTPS servers (httpbin.org)

These tests require internet connection and can be controlled by:
    UHTTP_SKIP_INTEGRATION=1     - skip all integration tests
    UHTTP_INTEGRATION_TIMEOUT=30 - timeout for requests (default: 30s)

Run only integration tests:
    python -m unittest tests.test_integration
"""
import os
import unittest
import socket

from uhttp import client as uhttp_client


SKIP_INTEGRATION = os.environ.get('UHTTP_SKIP_INTEGRATION', '').lower() in ('1', 'true', 'yes')
INTEGRATION_TIMEOUT = int(os.environ.get('UHTTP_INTEGRATION_TIMEOUT', '30'))
HTTPBIN_HOST = 'httpbin.org'


def is_httpbin_reachable():
    """Check if httpbin.org is reachable"""
    if SKIP_INTEGRATION:
        return False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((HTTPBIN_HOST, 443))
        sock.close()
        return True
    except (socket.error, socket.timeout, OSError):
        return False


HTTPBIN_AVAILABLE = is_httpbin_reachable()
SKIP_REASON = (
    "Integration tests disabled (UHTTP_SKIP_INTEGRATION=1)"
    if SKIP_INTEGRATION else
    f"httpbin.org not reachable"
)


@unittest.skipIf(not HTTPBIN_AVAILABLE, SKIP_REASON)
class TestHTTPIntegration(unittest.TestCase):
    """Test HTTP requests to httpbin.org"""

    def test_http_get(self):
        """Test basic HTTP GET request"""
        client = uhttp_client.HttpClient('http://httpbin.org')
        try:
            response = client.get('/get').wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertIn('headers', data)
            self.assertIn('Host', data['headers'])
        finally:
            client.close()

    def test_http_post_json(self):
        """Test HTTP POST with JSON data"""
        client = uhttp_client.HttpClient('http://httpbin.org')
        try:
            payload = {'name': 'test', 'value': 123}
            response = client.post('/post', json=payload).wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertEqual(data['json'], payload)
        finally:
            client.close()

    def test_http_query_params(self):
        """Test HTTP GET with query parameters"""
        client = uhttp_client.HttpClient('http://httpbin.org')
        try:
            response = client.get('/get', query={'foo': 'bar', 'num': '42'}).wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertEqual(data['args']['foo'], 'bar')
            self.assertEqual(data['args']['num'], '42')
        finally:
            client.close()

    def test_http_custom_headers(self):
        """Test HTTP GET with custom headers"""
        client = uhttp_client.HttpClient('http://httpbin.org')
        try:
            response = client.get('/headers', headers={
                'X-Custom-Header': 'test-value'
            }).wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertEqual(data['headers'].get('X-Custom-Header'), 'test-value')
        finally:
            client.close()


@unittest.skipIf(not HTTPBIN_AVAILABLE, SKIP_REASON)
class TestHTTPSIntegration(unittest.TestCase):
    """Test HTTPS requests to httpbin.org"""

    def test_https_get(self):
        """Test basic HTTPS GET request"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            response = client.get('/get').wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertIn('headers', data)
        finally:
            client.close()

    def test_https_post_json(self):
        """Test HTTPS POST with JSON data"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            payload = {'secure': True, 'data': 'test'}
            response = client.post('/post', json=payload).wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertEqual(data['json'], payload)
        finally:
            client.close()

    def test_https_keep_alive(self):
        """Test HTTPS with multiple requests on same connection"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            # First request
            response1 = client.get('/get', query={'req': '1'}).wait()
            self.assertEqual(response1.status, 200)

            # Second request on same connection
            response2 = client.get('/get', query={'req': '2'}).wait()
            self.assertEqual(response2.status, 200)

            # Third request
            response3 = client.get('/get', query={'req': '3'}).wait()
            self.assertEqual(response3.status, 200)
        finally:
            client.close()

    def test_https_binary_response(self):
        """Test HTTPS binary response (image)"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            response = client.get('/image/png').wait()
            self.assertEqual(response.status, 200)
            self.assertIn('image/png', response.content_type)
            # PNG magic bytes
            self.assertTrue(response.data.startswith(b'\x89PNG'))
        finally:
            client.close()

    def test_https_expect_100_continue(self):
        """Test Expect: 100-continue with real server"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            body = b'test data for 100 continue'
            response = client.post(
                '/post', data=body, expect_continue=True).wait()
            self.assertEqual(response.status, 200)
            # httpbin echoes back the data
            self.assertEqual(response.json()['data'], body.decode())
        finally:
            client.close()


@unittest.skipIf(not HTTPBIN_AVAILABLE, SKIP_REASON)
class TestHTTPSAuthIntegration(unittest.TestCase):
    """Test HTTPS authentication with httpbin.org"""

    def test_basic_auth_success(self):
        """Test successful basic auth over HTTPS"""
        client = uhttp_client.HttpClient(
            'https://httpbin.org',
            auth=('testuser', 'testpass')
        )
        try:
            response = client.get('/basic-auth/testuser/testpass').wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertTrue(data['authenticated'])
            self.assertEqual(data['user'], 'testuser')
        finally:
            client.close()

    def test_basic_auth_failure(self):
        """Test failed basic auth over HTTPS"""
        client = uhttp_client.HttpClient(
            'https://httpbin.org',
            auth=('wrong', 'credentials')
        )
        try:
            response = client.get('/basic-auth/testuser/testpass').wait()
            self.assertEqual(response.status, 401)
        finally:
            client.close()


@unittest.skipIf(not HTTPBIN_AVAILABLE, SKIP_REASON)
class TestHTTPSStatusCodes(unittest.TestCase):
    """Test various HTTP status codes over HTTPS"""

    def test_status_404(self):
        """Test 404 Not Found"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            response = client.get('/status/404').wait()
            self.assertEqual(response.status, 404)
        finally:
            client.close()

    def test_status_500(self):
        """Test 500 Internal Server Error"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            response = client.get('/status/500').wait()
            self.assertEqual(response.status, 500)
        finally:
            client.close()

    def test_redirect_follow(self):
        """Test that redirects are NOT automatically followed"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            response = client.get('/redirect/1').wait()
            # Client doesn't follow redirects automatically
            self.assertEqual(response.status, 302)
        finally:
            client.close()


@unittest.skipIf(not HTTPBIN_AVAILABLE, SKIP_REASON)
class TestHTTPMethods(unittest.TestCase):
    """Test various HTTP methods over HTTPS"""

    def test_put(self):
        """Test PUT request"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            response = client.put('/put', json={'key': 'value'}).wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertEqual(data['json'], {'key': 'value'})
        finally:
            client.close()

    def test_delete(self):
        """Test DELETE request"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            response = client.delete('/delete').wait()
            self.assertEqual(response.status, 200)
        finally:
            client.close()

    def test_patch(self):
        """Test PATCH request"""
        client = uhttp_client.HttpClient('https://httpbin.org')
        try:
            response = client.patch('/patch', json={'update': True}).wait()
            self.assertEqual(response.status, 200)
            data = response.json()
            self.assertEqual(data['json'], {'update': True})
        finally:
            client.close()


if __name__ == '__main__':
    unittest.main()
