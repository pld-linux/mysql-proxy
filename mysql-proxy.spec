# TODO
# - system lua-lfs for tests (LuaFileSystem 1.2)
# - daemon does not close its std fds
# - tests need fixing (can't find libs it built)
# OLD TODO
# - rw splitting bug: http://bugs.mysql.com/bug.php?id=36505
#   http://jan.kneschke.de/2007/8/26/mysql-proxy-more-r-w-splitting
#   http://www.teonator.net/2008/11/25/drupal-read-write-splitting/
#   http://dailyvim.blogspot.com/2008/07/mysql-high-availability-sandbox-proxy.html
#   https://launchpad.net/mysql-sandbox
#
# Conditional build:
%bcond_with	tests		# build with tests. needs mysql server on localhost:3306

Summary:	MySQL Proxy
Summary(pl.UTF-8):	Proxy MySQL
Name:		mysql-proxy
Version:	0.8.0
Release:	0.11
License:	GPL
Group:		Applications/Networking
Source0:	http://launchpad.net/mysql-proxy/0.8/%{version}/+download/%{name}-%{version}.tar.gz
# Source0-md5:	b6a9748d72e8db7fe3789fbdd60ff451
Source1:	%{name}.init
Source2:	%{name}.sysconfig
Source3:	%{name}.conf
URL:		http://forge.mysql.com/wiki/MySQL_Proxy
BuildRequires:	autoconf
BuildRequires:	automake
BuildRequires:	glib2-devel >= 1:2.4.0
BuildRequires:	libevent-devel
BuildRequires:	libtool
BuildRequires:	lua51-devel
BuildRequires:	mysql-devel
BuildRequires:	pkgconfig
BuildRequires:	rpmbuild(macros) >= 1.268
BuildRequires:	sed >= 4.0
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
Requires:	rc-scripts >= 0.4.1.24
Provides:	group(mysqlproxy)
Provides:	user(mysqlproxy)
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%define		_includedir	%{_prefix}/include/%{name}

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

%prep
%setup -q

sed -i -e 's/g_build_filename(base_dir, "lib"/g_build_filename(base_dir, "%{_lib}"/g' src/chassis.c
sed -i -e 's/g_build_filename(srv->base_dir, "lib"/g_build_filename(srv->base_dir, "%{_lib}"/g' src/chassis.c

%build
%{__libtoolize}
%{__aclocal} -I m4
%{__autoconf}
%{__autoheader}
%{__automake}
%configure \
	--with-lua=lua51
%{__make}

%if %{with tests}
export MYSQL_USER=mysql
export MYSQL_PASSWORD=
export MYSQL_HOST=localhost
export MYSQL_DB=test
%{__make} -C tests/suite check
%endif

%install
rm -rf $RPM_BUILD_ROOT
%{__make} install \
	DESTDIR=$RPM_BUILD_ROOT

install -d $RPM_BUILD_ROOT{/etc/{rc.d/init.d,sysconfig},%{_sysconfdir}/%{name},/var/log/{archive,}/%{name}}
install -p %{SOURCE1} $RPM_BUILD_ROOT/etc/rc.d/init.d/%{name}
cp -a %{SOURCE2} $RPM_BUILD_ROOT/etc/sysconfig/%{name}
cp -a %{SOURCE3} $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/%{name}.conf

# daemon in sbindir
install -d $RPM_BUILD_ROOT%{_sbindir}
mv $RPM_BUILD_ROOT{%{_bindir},%{_sbindir}}/mysql-proxy

# noarch data to /usr/share
install -d $RPM_BUILD_ROOT%{_datadir}/%{name}/lua
mv $RPM_BUILD_ROOT{%{_libdir},%{_datadir}}/%{name}/lua/proxy

rm -f $RPM_BUILD_ROOT%{_libdir}/%{name}/plugins/*.la
rm -f $RPM_BUILD_ROOT%{_libdir}/%{name}/lua/*.la

# no -devel, kill
rm -rf $RPM_BUILD_ROOT%{_includedir}
rm -rf $RPM_BUILD_ROOT%{_libdir}/libmysql-*.la
rm -rf $RPM_BUILD_ROOT%{_libdir}/libmysql-*.so
rm -rf $RPM_BUILD_ROOT%{_pkgconfigdir}

# put those to -tutorial package
rm -f $RPM_BUILD_ROOT%{_datadir}/*.lua

%clean
rm -rf $RPM_BUILD_ROOT

%pre
%groupadd -g 193 mysqlproxy
%useradd -u 193 -g mysqlproxy -c "MySQL Proxy" mysqlproxy

%post
/sbin/ldconfig
/sbin/chkconfig --add %{name}
%service %{name} restart "MySQL Proxy"

%preun
if [ "$1" = "0" ]; then
	%service -q %{name} stop
	/sbin/chkconfig --del %{name}
fi

%postun
/sbin/ldconfig
if [ "$1" = "0" ]; then
	%userremove mysqlproxy
	%groupremove mysqlproxy
fi

%files
%defattr(644,root,root,755)
%doc AUTHORS NEWS README* ChangeLog
%attr(754,root,root) /etc/rc.d/init.d/%{name}
%config(noreplace) %verify(not md5 mtime size) /etc/sysconfig/%{name}
%dir %attr(750,root,root) %{_sysconfdir}/%{name}
%config(noreplace) %attr(640,root,root) %verify(not md5 mtime size) %{_sysconfdir}/%{name}/%{name}.conf
%attr(755,root,root) %{_sbindir}/%{name}

%attr(750,root,mysqlproxy) %dir /var/log/%{name}
%attr(750,root,mysqlproxy) %dir /var/log/archive/%{name}

# ??? tools?
%attr(755,root,root) %{_bindir}/mysql-binlog-dump
%attr(755,root,root) %{_bindir}/mysql-myisam-dump

%dir %{_libdir}/%{name}
%dir %{_libdir}/%{name}/lua
%attr(755,root,root) %{_libdir}/%{name}/lua/chassis.so
%attr(755,root,root) %{_libdir}/%{name}/lua/glib2.so
%attr(755,root,root) %{_libdir}/%{name}/lua/lfs.so
%attr(755,root,root) %{_libdir}/%{name}/lua/lpeg.so
%attr(755,root,root) %{_libdir}/%{name}/lua/mysql.so
%attr(755,root,root) %{_libdir}/%{name}/lua/posix.so

%dir %{_datadir}/%{name}/lua/proxy
%{_datadir}/%{name}/lua/proxy/auto-config.lua
%{_datadir}/%{name}/lua/proxy/balance.lua
%{_datadir}/%{name}/lua/proxy/commands.lua
%{_datadir}/%{name}/lua/proxy/parser.lua
%{_datadir}/%{name}/lua/proxy/test.lua
%{_datadir}/%{name}/lua/proxy/tokenizer.lua

%dir %{_libdir}/%{name}/plugins
%attr(755,root,root) %{_libdir}/%{name}/plugins/libadmin.so
%attr(755,root,root) %{_libdir}/%{name}/plugins/libdebug.so
%attr(755,root,root) %{_libdir}/%{name}/plugins/libproxy.so
%attr(755,root,root) %{_libdir}/%{name}/plugins/libreplicant.so

# -libs
%attr(755,root,root) %ghost %{_libdir}/libmysql-chassis-timing.so.0
%attr(755,root,root) %{_libdir}/libmysql-chassis-timing.so.*.*.*
%attr(755,root,root) %ghost %{_libdir}/libmysql-chassis.so.0
%attr(755,root,root) %{_libdir}/libmysql-chassis.so.*.*.*
%attr(755,root,root) %ghost %{_libdir}/libmysql-proxy.so.0
%attr(755,root,root) %{_libdir}/libmysql-proxy.so.*.*.*
