// @vitest-environment node
import { test } from "vitest";
import { PGlite } from '@electric-sql/pglite';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const root=new URL('../../', import.meta.url).pathname;
const schema=fs.readFileSync(root+'/supabase_schema.sql','utf8');
const upgrade=fs.readFileSync(root+'/backend/migrations/002_owner_isolation.sql','utf8');
for (const legacy of [false,true]) test(legacy ? "legacy PostgreSQL migration" : "fresh PostgreSQL migration", async () => {
 const db=new PGlite();
 if (legacy) await db.exec(schema.replace('    user_id UUID,\n    integration_name','    integration_name').replace('UNIQUE(user_id, integration_name)','UNIQUE(integration_name)'));
 await db.exec(schema); await db.exec(upgrade); await db.exec(schema); await db.exec(upgrade);
 const u='00000000-0000-0000-0000-000000000001', v='00000000-0000-0000-0000-000000000002';
 const {rows:[{id}]}=await db.query('INSERT INTO conversations(user_id,title) VALUES ($1,$2) RETURNING id',[u,'test']);
 await db.query('INSERT INTO messages(conversation_id,role,content) VALUES($1,$2,$3)',[id,'user','hello']);
 for (const owner of [u,v]) await db.query("INSERT INTO user_integrations(user_id,integration_name,access_token) VALUES($1,'google',$2) ON CONFLICT(user_id,integration_name) DO UPDATE SET access_token=EXCLUDED.access_token",[owner,owner]);
 assert.equal((await db.query('SELECT * FROM user_integrations')).rows.length,2);
 await db.query("INSERT INTO pending_actions VALUES ('one',$1,'tool','{}','chat',NOW()+INTERVAL '10 minutes')",[u]);
 assert.equal((await db.query("DELETE FROM pending_actions WHERE id='one' AND user_id=$1 RETURNING payload",[u])).rows.length,1);
 assert.equal((await db.query("DELETE FROM pending_actions WHERE id='one' AND user_id=$1 RETURNING payload",[u])).rows.length,0);
 await db.exec('BEGIN');await db.query('DELETE FROM conversations WHERE id=$1',[id]);await db.exec('ROLLBACK');
 assert.equal((await db.query('SELECT * FROM messages')).rows.length,1);
 await db.query('DELETE FROM conversations WHERE id=$1',[id]);assert.equal((await db.query('SELECT * FROM messages')).rows.length,0);
 const indexes=(await db.query("SELECT indexname FROM pg_indexes WHERE indexname IN ('idx_messages_history','idx_conversations_activity')")).rows;
 assert.equal(indexes.length,2);
 await db.close(); console.log((legacy?'Legacy upgrade':'Fresh schema')+': migration repeatability, composite ownership, one-time consumption, rollback, cascade, indexes passed');
}, 30000);
