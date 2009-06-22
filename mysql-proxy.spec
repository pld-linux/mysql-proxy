# TODO:
# - fix autotools
# - is URL correct?
# - is it stable version?
# - better descriptions

# Conditional build:
%bcond_with	tests		# build with tests. needs mysql server on localhost:3306
#
Summary:	MySQL Proxy
Summary(pl.UTF-8):	Proxy MySQL
Name:		mysql-proxy
Version:	0.7.1
Release:	0.1
License:	GPL
Group:		Applications/Networking
Source0:	ftp://sunsite.informatik.rwth-aachen.de/pub/mirror/www.mysql.com/Downloads/MySQL-Proxy/%{name}-%{version}.tar.gz
# Source0-md5:	009bc3e669fe42f5f8ac634d20226cf4
Source1:	%{name}.init
Source2:	%{name}.sysconfig
# From http://forge.mysql.com/tools/tool.php?id=81
Source3:	%{name}-logging.lua
Patch0:		%{name}-lua.patch
URL:		https://launchpad.net/mysql-proxy
BuildRequires:	autoconf
BuildRequires:	automake
BuildRequires:	glib2-devel >= 1:2.4.0
BuildRequires:	libevent-devel
BuildRequires:	libtool
BuildRequires:	lua51-devel
BuildRequires:	mysql-devel
BuildRequires:	rpmbuild(macros) >= 1.268
%if %{with tests}
BuildRequires:	check
BuildRequires:	lua51
%endif
Requires(post,preun):	/sbin/chkconfig
Requires(postun):	/usr/sbin/groupdel
Requires(postun):	/usr/sbin/userdel
Requires(pre):	/bin/id
Requires(pre):	/usr/bin/getgid
Requires(pre):	/usr/sbin/groupadd
Requires(pre):	/usr/sbin/useradd
Requires:	rc-scripts >= 0.4.0.20
Provides:	group(mysqlproxy)
Provides:	user(mysqlproxy)
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
MySQL Proxy is a simple program that sits between your client and
MySQL server(s) that can monitor, analyze or transform their
communication. Its flexibility allows for unlimited uses; common ones
include: load balancing; failover; query analysis; query filtering and
modification; and many more.

%description -l pl.UTF-8
MySQL Proxy to prosty program tkwiący między klienten a
serwerem/serwerami MySQL, potrafiący monitorować, analizować i
przekształcać ich komunikację. Jego elastyczność pozwala na
nieograniczone wykorzystanie; popularne sposoby użycia obejmują: load
balancing, failover, analizę zapytań, filtrowanie i modyfikowanie
zapytań... i wiele więcej.

%package libs
Summary:	MySQL Proxy libraries
Summary(pl.UTF-8):	Biblioteki MySQL Proxy
Group:		Libraries

%description libs
MySQL Proxy libraries.

%description libs -l pl.UTF-8
Biblioteki MySQL Proxy.

%package devel
Summary:	Header files for MySQL Proxy libraries
Summary(pl.UTF-8):	Pliki nagłówkowe bibliotek MySQL Proxy
Group:		Development/Libraries
Requires:	%{name}-libs = %{version}-%{release}

%description devel
Header files for MySQL Proxy libraries.

%description devel -l pl.UTF-8
Pliki nagłówkowe bibliotek MySQL Proxy.

%package plugins
Summary:	MySQL Proxy plugins
Summary(pl.UTF-8):	Wtyczki MySQL Proxy
Group:		Libraries

%description plugins
MySQL Proxy plugins.

%description plugins -l pl.UTF-8
Wtyczki MySQL Proxy.

%package script-logging
Summary:	Script for logging MySQL queries
Summary(pl.UTF-8):	Skrypt logujący zapytania MySQL
Group:		Libraries
Requires:	%{name} = %{epoch}:%{version}-%{release}

%description script-logging
Script for logging MySQL queries.

%description script-logging -l pl.UTF-8
Skrypt logujący zapytania MySQL.

%prep
%setup -q
%patch0 -p1

%build
#%%{__libtoolize}
#%%{__aclocal} -I m4
#%%{__autoconf}
#%%{__autoheader}
#%%{__automake}
%configure \
	--with-lua=lua51
%{__make}

%if %{with tests}
export MYSQL_USER=mysql
export MYSQL_PASSWORD=
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DB=test
%{__make} -C tests/suite check
%endif

%install
rm -rf $RPM_BUILD_ROOT
%{__make} install \
	DESTDIR=$RPM_BUILD_ROOT

# put those to -tutorial package
rm -f $RPM_BUILD_ROOT%{_datadir}/*.lua
rm -f $RPM_BUILD_ROOT%{_libdir}/mysql-proxy/plugins/*.la
install -d $RPM_BUILD_ROOT{/etc/{rc.d/init.d,sysconfig},/var/run/mysql-proxy}
install %{SOURCE1} $RPM_BUILD_ROOT/etc/rc.d/init.d/%{name}
install %{SOURCE2} $RPM_BUILD_ROOT/etc/sysconfig/%{name}
install %{SOURCE3} $RPM_BUILD_ROOT%{_libdir}/%{name}/lua/logging.lua

%clean
rm -rf $RPM_BUILD_ROOT

%pre
%groupadd -g 193 mysqlproxy
%useradd -u 193 -g mysqlproxy -c "MySQL Proxy" mysqlproxy

%post
/sbin/chkconfig --add %{name}
%service %{name} restart "MySQL Proxy"

%preun
if [ "$1" = "0" ]; then
	%service -q %{name} stop
	/sbin/chkconfig --del %{name}
fi

%postun
if [ "$1" = "0" ]; then
	%userremove mysqlproxy
	%groupremove mysqlproxy
fi

%files
%defattr(644,root,root,755)
%doc AUTHORS ChangeLog NEWS README README.TESTS THANKS
%attr(754,root,root) /etc/rc.d/init.d/%{name}
%config(noreplace) %verify(not md5 mtime size) /etc/sysconfig/%{name}
%attr(755,root,root) %{_sbindir}/mysql-proxy
%attr(755,root,root) %{_bindir}/mysql-binlog-dump
%attr(755,root,root) %{_bindir}/mysql-myisam-dump
%dir %{_libdir}/mysql-proxy
%{_libdir}/mysql-proxy/lua
%exclude %{_libdir}/mysql-proxy/lua/logging.lua
%dir %attr(775,root,mysqlproxy) /var/run/mysql-proxy

%files libs
%defattr(644,root,root,755)
%attr(755,root,root) %{_libdir}/libmysql-proxy.so.*.*
%attr(755,root,root) %ghost %{_libdir}/libmysql-proxy.so.0
%attr(755,root,root) %{_libdir}/libmysql-chassis.so.*.*
%attr(755,root,root) %ghost %{_libdir}/libmysql-chassis.so.0

%files devel
%defattr(644,root,root,755)
%{_libdir}/libmysql-proxy.so
%{_libdir}/libmysql-chassis.so
%{_libdir}/libmysql-proxy.la
%{_libdir}/libmysql-chassis.la

%files plugins
%defattr(644,root,root,755)
%dir %{_libdir}/mysql-proxy/plugins
%attr(755,root,root) %{_libdir}/mysql-proxy/plugins/*.so

%files script-logging
%defattr(644,root,root,755)
%{_libdir}/mysql-proxy/lua/logging.lua
