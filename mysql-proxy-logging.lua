--[[

   Copyright (C) 2007 MySQL AB

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

--]]

---
-- Uses MySQL-Proxy to log your queries
--
-- Written by Giuseppe Maxia, QA Developer
--[[
    Syntax : [SELECT] LOG option
    LOG HELP - returns this help
    LOG STATUS - displays logging status
    LOG FILE filename - sets a new file for logging (default /tmp/mysql.log)
    LOG {ENABLE|DISABLE} - enable/disable logging
    LOG {VERBOSE|NOVERBOSE} - enable/disable proxy verbose output
--]]

assert(proxy.PROXY_VERSION >= 0x00600,
   "you need at least mysql-proxy 0.6.0 to run this module")

local log_file = os.getenv("PROXY_LOG_FILE")
local DEBUG = os.getenv("DEBUG") or 0
DEBUG = DEBUG + 0

if (log_file == nil) then
    log_file = "/tmp/mysql.log"
end

local fh = io.open(log_file, "a+")
local is_proxy_query = false
local active_logging = true

local help_dataset = {
    fields = { 
        { type = proxy.MYSQL_TYPE_STRING, name = 'log syntax' }
    },
    rows = { 
        {'syntax: [SELECT] LOG option'},
        {"LOG HELP - returns this help"},
        {"LOG STATUS - displays logging status"},
        {"LOG FILE filename - sets a new file for logging (default /tmp/mysql.log)"},
        {"LOG {ENABLE|DISABLE} - enable/disable logging"},
        {"LOG {VERBOSE|NOVERBOSE} - enable/disable proxy verbose output"},
    }
} 

function dataset (ds) 
    proxy.response.type = proxy.MYSQLD_PACKET_OK
    proxy.response.resultset = ds
    return proxy.PROXY_SEND_RESULT
end

function simple_dataset (header, message) 
    proxy.response.type = proxy.MYSQLD_PACKET_OK
    proxy.response.resultset = {
        fields = {{type = proxy.MYSQL_TYPE_STRING, name = header}},
        rows = { { message} }
    }
    return proxy.PROXY_SEND_RESULT
end

function read_query( packet )
    if packet:byte() ~= proxy.COM_QUERY then
        return
    end
    is_proxy_query = false
    local query = packet:sub(2)
    if query:match('^[Ll][Oo][Gg]') 
        or query:match('^%s*[Ss][Ee][Ll][Ee][Cc][Tt]%s+[Ll][Oo][Gg]%s') 
    then
        local tokens = proxy.tokenizer.tokenize(query)
        local START_QUERY = 1
        if ( DEBUG > 1) then
            for i = 1, #tokens do
                print (tokens[i]['token_id'] , tokens[i]['token_name'], tokens[i]['text']  )
            end
        end
        if tokens[1]['token_name'] == 'TK_SQL_SELECT' then
            START_QUERY = 2
        end
        if tokens[START_QUERY +1]['text']:lower() == 'file' 
           and 
           tokens[START_QUERY + 2]['token_name'] == 'TK_STRING' 
        then
            log_file = tokens[START_QUERY + 2]['text']
            fh:close()
            fh = io.open(log_file, "a+")
            is_proxy_query = true
            logging_enabled = true 
            return simple_dataset('info', string.format('log file set to %s',log_file)) 
        elseif 
                tokens[START_QUERY +1]['text']:lower() == 'help' 
        then
            is_proxy_query = true
            return dataset(help_dataset)
        elseif 
                tokens[START_QUERY +1]['text']:lower() == 'enable' 
        then
            is_proxy_query = true
            logging_enabled = true 
            return simple_dataset('info','logging enabled' )
        elseif 
                tokens[START_QUERY +1]['text']:lower() == 'disable' 
        then
            is_proxy_query = true
            logging_enabled = false 
            return simple_dataset('info','logging disabled') 
        elseif 
                tokens[START_QUERY +1]['text']:lower() == 'verbose' 
        then
            is_proxy_query = true
            DEBUG = 1 
            return simple_dataset('info','log server verbose enabled') 
        elseif 
                tokens[START_QUERY +1]['text']:lower() == 'noverbose' 
        then
            is_proxy_query = true
            DEBUG = 0
            return simple_dataset('info','log server verbose disabled') 
        elseif 
                tokens[START_QUERY +1]['text']:lower() == 'status' 
        then
            is_proxy_query = true
            local active_logging = '';
            local verbose_logging = '';
            if (DEBUG > 0) then
                verbose_logging = '(verbose)'
            end
            if logging_enabled == false then
                active_logging = 'not'
            end
            return simple_dataset('log status', string.format('logging to file %s %s active %s',
                log_file,
                active_logging,
                verbose_logging))
        end
    end
    proxy.queries:append(1, string.char(proxy.COM_QUERY) .. query) 
    return proxy.PROXY_SEND_QUERY
end

function read_query_result (inj)
  local row_count = 0
  local res = assert(inj.resultset)
  local num_cols = string.byte(res.raw, 1)
  if num_cols > 0 and num_cols < 255 then
    for row in inj.resultset.rows do
      row_count = row_count + 1
    end
  end
  local error_status =""
  if res.query_status and (res.query_status < 0 ) then
        error_status = "[ERR]"
  end
  if (res.affected_rows) then
        row_count = string.format('>{%d}',res.affected_rows)
    else
        row_count = string.format('<{%d}',row_count)
  end
  --
  -- write the query, adding the number of retrieved rows
  --
  local out_string = string.format("%s %6d -- %s %s %s", 
      os.date('%Y-%m-%d %H:%M:%S'), 
      proxy.connection.server["thread_id"], 
      inj.query, 
      row_count,
      error_status)
  if logging_enabled == false then return end
  if DEBUG > 0 then
        print (out_string)
  end
  fh:write(out_string .. "\n")
  fh:flush()
end

--[[

    Sample log

2007-06-29 16:41:10     33 -- show databases <{5} 
2007-06-29 16:41:10     33 -- show tables <{2} 
2007-06-29 16:41:12     33 -- Xhow tables <{0} [ERR]
2007-06-29 16:44:27     34 -- select * from t1 <{6} 
2007-06-29 16:44:50     34 -- update t1 set id = id * 100 where c = 'a' >{2} 
2007-06-29 16:45:53     34 -- insert into t1 values (10,'aa') >{1} 
2007-06-29 16:46:07     34 -- insert into t1 values (20,'aa'),(30,'bb') >{2} 
2007-06-29 16:46:22     34 -- delete from t1 >{9} 

The columns show date,  time, connection id, and query.
The number on braces after the query is the retrieved rows (for SELECT) <{x}
or affected rows (for INSERT/DELETE/UPDATE) >{x}
If an error occurs, an "ERR" in bracket is printed at the end of the row

--]]
