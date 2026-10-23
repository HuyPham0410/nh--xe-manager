const test = require('node:test');
const assert = require('node:assert/strict');
const { config } = require('../server');

test('default ports preserve the existing application addresses', () => {
  assert.deepEqual(config({}), { webPort: 3000, backendPort: 8765, python: 'python' });
});
test('custom settings route each service to a different port', () => {
  assert.deepEqual(config({ PORT: '3010', BACKEND_PORT: '8770', PYTHON_COMMAND: 'C:\\Python\\python.exe' }), {
    webPort: 3010, backendPort: 8770, python: 'C:\\Python\\python.exe',
  });
});
test('invalid and conflicting ports fail before starting services', () => {
  for (const value of ['abc', '0', '80', '65536', '3000.5', '3000;echo bad', '']) {
    assert.throws(() => config({ PORT: value }));
  }
  assert.throws(() => config({ PORT: '8765' }), /different/);
});
