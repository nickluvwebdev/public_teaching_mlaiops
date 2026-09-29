import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';
const handling = new Trend('server_handling_ms');
const scoring = new Trend('server_scoring_ms');
const rows = Number(__ENV.BATCH || 1);
const base = {temp_c:78.4,vibration_mm_s:3.1,pressure_kpa:315.2,hours_since_service:4200,load_pct:68,ambient_humidity:55};
const payload = JSON.stringify(rows > 1 ? {rows:Array(rows).fill(base)} : {...base,padding:'x'.repeat(Number(__ENV.PADDING || 0))});
export const options = {
  vus: Number(__ENV.VUS || 10), duration: __ENV.DURATION || '30s',
  summaryTrendStats: ['avg','min','med','max','p(50)','p(95)','p(99)'],
  thresholds: {http_req_duration:['p(95)<500'],http_req_failed:['rate<0.01']},
};
export default function () {
  const response = http.post(__ENV.TARGET+(rows>1?'/predict/batch':'/predict'),payload,{
    headers:{'Content-Type':'application/json','Authorization':'Bearer '+__ENV.TOKEN},timeout:'60s'});
  handling.add(Number(response.headers['X-Server-Latency-Ms'] || 0));
  scoring.add(Number(response.headers['X-Scoring-Ms'] || 0));
  check(response, {'HTTP 200':r=>r.status===200,'version present':r=>!!r.headers['X-Model-Version']});
}
export function handleSummary(data) {
  return { [__ENV.SUMMARY || '/results/summary.json']: JSON.stringify(data,null,2) };
}
