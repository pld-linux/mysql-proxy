--[[ $%BEGINLICENSE%$
 Copyright (C) 2008 MySQL AB, 2008 Sun Microsystems, Inc

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; version 2 of the License.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

 $%ENDLICENSE%$ --]]


---
-- a flexible statement based load balancer with connection pooling
--
-- * build a connection pool of min_idle_connections for each backend and 
--   maintain its size
-- * reusing a server-side connection when it is idling
-- * By glenn@telenet.be:
-- * Fixed issues with parameters for mysql-proxy 0.7.2.: (Lenny debian backports version)
-- * Works on :
-- mysql-proxy 0.7.2
--  glib2: 2.16.6
--  libevent: 1.3e
--  lua: Lua 5.1.3
--    LUA_PATH: /usr/lib/mysql-proxy/lua/?.lua
--    LUA_CPATH: /usr/lib/mysql-proxy/lua/?.so
--  == plugins ==
--  admin: 0.7.0
--  proxy: 0.7.0
-- * I merged the reporter.lua plugin into this as well so I can be used with the admin-1.lua script without 
-- * Having to use the multi-lua script setup.  I use this proxy to pool slave connection. I do not need the 
-- * master/slave splitting (So be careful) as I only send slaves those queries.

--- config
proxy.global.query_counter = proxy.global.query_counter or 0

--
-- connection pool
local min_idle_connections = 2
local max_idle_connections = 6

-- debug
local is_debug = false

--- end of config

---
-- read/write splitting sends all non-transactional SELECTs to the slaves
--
-- is_in_transaction tracks the state of the transactions
local is_in_transaction = 0

--- 
-- get a connection to a backend
--
-- as long as we don't have enough connections in the pool, create new connections
--
function connect_server() 
	-- make sure that we connect to each backend at least ones to 
	-- keep the connections to the servers alive
	--
	-- on read_query we can switch the backends again to another backend

	if is_debug then
		print()
		print("[connect_server] ")
	end

	local least_idle_conns_ndx = 0
	local least_idle_conns = 0

	for i = 1, #proxy.global.backends do
		local backend = proxy.global.backends[i]
		-- we don't have a username yet, try to find a connections which is idling
		local pool     = backend.pool
		local cur_idle = (pool.users[""].cur_idle_connections or 0)

		if is_debug then
			print("  [".. i .."].backend.connected_clients = " .. (backend.connected_clients or "(nil)"))
			print("  [".. i .."].backend.type = " .. (backend.type or "(nil)"))
			print("  [".. i .."].backend.state = " .. (backend.state or "(nil)"))
			-- print("  [".. i .."].backend.address = " .. (backend.dst.name or "(nil)"))
			-- print("  Server address = " .. (backend.connection.server.dst.name or "(nil)"))
			-- print("  [".. i .."].backend.dst = " .. (backend.dst or "(nil)"))
			print("  [".. i .."].backend.uuid = " .. (backend.uuid or "(nil)"))
			print("  [".. i .."].least_idle_conns = " .. (least_idle_conns or "(nil)"))
			print("  [".. i .."].least_idle_conns_ndx = " .. (least_idle_conns_ndx or "(nil)"))
			print("  [".. i .."].cur_idle = " .. (cur_idle or "(nil)"))
			-- print("  [".. i .."].backend.idling_connections = " .. (bs.idling_connections or "(nil)"))
		end

		if backend.state ~= proxy.BACKEND_STATE_DOWN then
			-- try to connect to each backend once at least
			if cur_idle == 0 then
				proxy.connection.backend_ndx = i
				if is_debug then
					print("  [".. i .."] open new connection")
				print("[connect_server] " .. (proxy.connection.client.src.name or "(nil)"))
					print("We have " .. #proxy.global.backends .. " backends:")
				end
				return
			end

			-- try to open at least min_idle_connections
			if least_idle_conns_ndx == 0 or ( cur_idle < min_idle_connections and cur_idle < least_idle_conns ) then
				least_idle_conns_ndx = i
				-- least_idle_conns = backend.idling_connections
				least_idle_conns = cur_idle
			end
		end
	end

	if least_idle_conns_ndx > 0 then
		proxy.connection.backend_ndx = least_idle_conns_ndx
	end

	if proxy.connection.backend_ndx > 0 then 
		local backend = proxy.global.backends[proxy.connection.backend_ndx]
		local pool     = backend.pool -- we don't have a username yet, try to find a connections which is idling
		local cur_idle = pool.users[""].cur_idle_connections

		if cur_idle >= min_idle_connections then
			-- we have 4 idling connections in the pool, that's good enough
			if is_debug then
				print("  using pooled connection from: " .. (proxy.connection.backend_ndx or "(nil)"))
			end
	
			return proxy.PROXY_IGNORE_RESULT
		end
	end

	if is_debug then
		print("  opening new connection on: " .. (proxy.connection.backend_ndx or "(nil)"))
	end

	-- open a new connection 
end

--- 
-- put the successfully authed connection into the connection pool
--
-- @param auth the context information for the auth
--
-- auth.packet is the packet
function read_auth_result( auth )
	local state = auth.packet:byte()
	if state == proxy.MYSQLD_PACKET_OK then
		proxy.global.initialize_process_table()
		table.insert( proxy.global.process[proxy.connection.server.thread_id],
			{ ip = proxy.connection.client.src.name, ts = os.time() } )
		-- auth was fine, disconnect from the server
		proxy.connection.backend_ndx = 0
	elseif auth.packet:byte() == proxy.MYSQLD_PACKET_EOF then
		-- we received either a 
		-- 
		-- * MYSQLD_PACKET_ERR and the auth failed or
		-- * MYSQLD_PACKET_EOF which means a OLD PASSWORD (4.0) was sent
		print("(read_auth_result) ... not ok yet");
	elseif auth.packet:byte() == proxy.MYSQLD_PACKET_ERR then
		-- auth failed
	end
end

---
-- from reporter.lua import
--[[
	See http://forge.mysql.com/tools/tool.php?id=78
	(Thanks to Jan Kneschke)
	See http://www.chriscalender.com/?p=41
	(Thanks to Chris Calender)
	See http://datacharmer.blogspot.com/2009/01/mysql-proxy-is-back.html
	(Thanks Giuseppe Maxia)
--]]

function proxy.global.initialize_process_table()
	if proxy.global.process == nil then
		proxy.global.process = {}
	end
	if proxy.global.process[proxy.connection.server.thread_id] == nil then
		proxy.global.process[proxy.connection.server.thread_id] = {}
	end
end
-- end reporter.lua import

--- 
-- read/write splitting - read_query() can return a resultset
--
-- You can use read_query() to return a result-set.
--
-- @param packet the mysql-packet sent by the client
--
-- @return
--   * nothing to pass on the packet as is,
--   * proxy.PROXY_SEND_QUERY to send the queries from the proxy.queries queue
--   * proxy.PROXY_SEND_RESULT to send your own result-set
--
function read_query( packet ) 
	-- a new query came in in this connection
	-- using proxy.global.* to make it available to the admin plugin
	proxy.global.query_counter = proxy.global.query_counter + 1


	if is_debug then
		print("[read_query]")
		print("  authed backend = " .. (proxy.connection.backend_ndx or "(nil)"))
		print("  used db = " .. (proxy.connection.client.default_db or "(nil)"))
		print("  Client address = " .. (proxy.connection.client.src.name or "(nil)"))
	end
--		print("  .least_idle_conns = " .. (least_idle_conns or "(nil)"))
--		print("  .least_idle_conns_ndx = " .. (least_idle_conns_ndx or "(nil)"))
--		print("  .cur_idle = " .. (cur_idle or "(nil)"))
--		print("  .type = " .. (proxy.connection.backend.type or "(nil)"))
--		print("  .state = " .. (proxy.connection.backend.state or "(nil)"))
--		print("  .uuid = " .. (proxy.connection.backend.uuid or "(nil)"))
--		print("  .src.name = " .. (proxy.connection.backend.src.name or "(nil)"))
--		print("  .backend.idling_connections = " .. (proxy.connection.backend.idling_connections or "(nil)"))

	if packet:byte() == proxy.COM_QUIT then
		-- don't send COM_QUIT to the backend. We manage the connection
		-- in all aspects.
		proxy.response = {
			type = proxy.MYSQLD_PACKET_OK,
		}

		return proxy.PROXY_SEND_RESULT
	end

	if proxy.connection.backend_ndx == 0 then
		-- we don't have a backend right now
		-- 
		-- let's pick a master as a good default
		for i = 1, #proxy.global.backends do
			local backend = proxy.global.backends[i]
			local pool     = backend.pool -- we don't have a username yet, try to find a connections which is idling
			local cur_idle = pool.users[proxy.connection.client.username].cur_idle_connections
			
			if cur_idle > 0 and 
				backend.state ~= proxy.BACKEND_STATE_DOWN and 
				backend.type == proxy.BACKEND_TYPE_RW then
				proxy.connection.backend_ndx = i
				break
			end
		end
	end

	if true or proxy.connection.client.default_db and proxy.connection.client.default_db ~= proxy.connection.server.default_db then
		-- sync the client-side default_db with the server-side default_db
		proxy.queries:append(2, string.char(proxy.COM_INIT_DB) .. proxy.connection.client.default_db, { resultset_is_needed = true })
	end
	proxy.queries:append(1, packet)

	return proxy.PROXY_SEND_QUERY
end

---
-- as long as we are in a transaction keep the connection
-- otherwise release it so another client can use it
function read_query_result( inj ) 
	local res      = assert(inj.resultset)
	local flags    = res.flags

	if inj.id ~= 1 then
		-- ignore the result of the USE <default_db>
		return proxy.PROXY_IGNORE_RESULT
	end
	is_in_transaction = flags.in_trans

	if not is_in_transaction then
		-- release the backend
		proxy.connection.backend_ndx = 0
	end
end

--- 
-- close the connections if we have enough connections in the pool
--
-- @return nil - close connection 
--         IGNORE_RESULT - store connection in the pool

function disconnect_client()
	if proxy.connection.backend_ndx == 0 then
		-- currently we don't have a server backend assigned
		--
		-- pick a server which has too many idling connections and close one
		for i = 1, #proxy.global.backends do
			local backend = proxy.global.backends[i]
			local pool     = backend.pool -- we don't have a username yet, try to find a connections which is idling
			local cur_idle = pool.users[proxy.connection.client.username].cur_idle_connections
			if is_debug then
				print("  [".. i .."] idling: " .. (cur_idle or "(nil)"))
			end

			if backend.state ~= proxy.BACKEND_STATE_DOWN and cur_idle > max_idle_connections then
				if is_debug then
					print("  [".. i .."] closing connection, idling: " .. (cur_idle or "(nil)"))
				end
				-- try to disconnect a backend
				proxy.connection.backend_ndx = i
				return
			end
		end
	end
end
