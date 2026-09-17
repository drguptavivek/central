const { assert } = require('../lib');
const request = require('./request');

const baseUrl = 'https://localhost:11001';

describe('VG development WAF boundary', () => {
  it('allows Vite virtual modules through the development frontend proxy', async () => {
    const res = await request(`${baseUrl}/@id/__x00__plugin-vue:export-helper`);

    assert.equal(res.status, 200);
    assert.equal(await res.text(), 'OK');
  });

  it('keeps the same CRS signature blocked under the API proxy', async () => {
    const res = await request(`${baseUrl}/v1/@id/__x00__plugin-vue:export-helper`);

    assert.equal(res.status, 403);
  });
});
