附录C 模块编译，调试与测试
======================================



C.1 编译与安装
++++++++++++++++++++

环境要求
^^^^^^^^^^^^^^^^^^^^^^^^

    操作系统：目前Nginx各版本在以下操作系统和平台测试通过：
    
        FreeBSD 3  — 10 / i386; FreeBSD 5  — 10 / amd64;
        
        Linux 2.2  — 3 / i386; Linux 2.6  — 3 / amd64;
        
        Solaris 9 / i386, sun4u; Solaris 10 / i386, amd64, sun4v;
        
        AIX 7.1 / powerpc;
        
        HP-UX 11.31 / ia64;
        
        MacOS X / ppc, i386;
        
        Windows XP, Windows Server 2003
        
    磁盘空间：必须保证至少10M以上的磁盘工具，并且随着编译设置及第三方模块的安装而有所不同；
    
    编译器及相关工具： 必须确保操作系统安装有GCC编译器；Autoconf和Automake工具；用户可通过yum命令安装编译器及相关工具：yum -y install gcc gcc-c++ autoconf automake；
    模块依赖性：Nginx的一些模块需要第三方库的支持，如rewrite模块需要pcre库，gzip模块需要zlib模块，ssl功能你需要openssl库等。用户可通过yum命令安装这些依赖库：yum -y install pcre pcre-devel zlib zlib-devel openssl openssl-devel；
        
        
下载
^^^^^^^^^^^^^^^^^^^^^^^^

Nginx是开源软件，用户可以访问 http://nginx.org/ 网站获取源码包或Windows二进制文件下载。其中1.3.x版本为开发版本，1.2.x版本为稳定版本。开发版本分支会较快的获得新功能和缺陷修复，但同时也可能会遇到新的缺陷。一旦更新稳定下来，就会被加入稳定版本分支。

作为生产环境，通常建议用户使用稳定版本。

Nginx在Windows环境下安装
^^^^^^^^^^^^^^^^^^^^^^^^

    nginx的windows版本使用原生win32 API（非Cygwin模拟层）。当前存在的已知问题：1.采用select作为通知方法，所以不具备很高的性能和扩展性；2.虽然可以启动若干工作进程运行，实际上只有一个进程在处理请求所有请求；3.一个工作进程只能处理不超过1024个并发连接；4.缓存和其他需要共享内存支持的模块在windows vista及后续版本的操作系统中无法工作，因为在这些操作系统中，地址空间的布局是随机的；5.除了XSLT过滤器、图像过滤器、GeoIP模块和嵌入Perl语言支持以外，Nginx的Windows版本与Unix版本相比，功能几乎齐全。

    安装Nginx的Windows版本，建议下载最新的1.3.13开发版本，因为开发分支上包含了所有已知的问题修复，尤其是针对Windows版本的问题修复。解压下载得到的zip文件，进入nginx-1.3.13目录，运行nginx。

    
        C盘根目录下安装例子
        
.. code::

        cd c:\
        unzip nginx-1.3.13.zip
        cd nginx-1.3.13
        start nginx

        Nginx的Windows版本的控制命令包含如下：
        
.. code:: c

        nginx -s stop 快速退出
        nginx -s quit 优雅退出
        nginx -s reload 更换配置，启动新的工作进程，优雅的关闭以往的工作进程
        nginx -s reopen 重新打开日志文件

Nginx在Linux环境下安装
^^^^^^^^^^^^^^^^^^^^^^^^

        Nginx在Linux环境下可以通过编译源码的方式安装，最简单的安装命令如下：
        
.. code:: c

        wget http://nginx.org/download/nginx-1.2.0.tar.gz
        tar zxvf nginx-1.2.0.tar.gz
        cd nginx-1.2.0
        ./configure
        make
        sudo make install
        
按照以上命令，Nginx将被默认安装到/usr/local/nginx目录下。用户可以通过./configure --help命令查看Nginx可选择的编译选项进行自定义安装配置。

        Nginx的configure脚本支持以下选项:

.. code:: c

        --prefix=<PATH> #Nginx安装路径。如果没有指定，默认为 /usr/local/nginx

        --sbin-path=<PATH> #Nginx可执行文件安装路径。只能安装时指定，如果没有指定，默认为<prefix>/sbin/nginx

        --conf-path=<PATH> #在没有给定-c选项下默认的nginx.conf的路径。如果没有指定，默认为<prefix>/conf/nginx.conf 

        --pid-path=<PATH> #在nginx.conf中没有指定pid指令的情况下，默认的nginx.pid的路径。如果没有指定，默认为 <prefix>/logs/nginx.pid

        --lock-path=<PATH> #nginx.lock文件的路径

        --error-log-path=<PATH> #在nginx.conf中没有指定error_log指令的情况下，默认的错误日志的路径。如果没有指定，默认为 <prefix>/logs/error.log

        --http-log-path=<PATH> #在nginx.conf中没有指定access_log指令的情况下，默认的访问日志的路径。如果没有指定，默认为 <prefix>/logs/access.log。

        --user=<USER> #在nginx.conf中没有指定user指令的情况下，默认的nginx使用的用户。如果没有指定，默认为 nobody 

        --group=<GROUP> #在nginx.conf中没有指定user指令的情况下，默认的nginx使用的组。如果没有指定，默认为 nobody

        --builddir=DIR #指定编译的目录

        --with-rtsig_module #启用 rtsig 模块

        --with-select_module(--without-select_module) #允许或不允许开启SELECT模式，如果configure没有找到合适的模式，比如，kqueue(sun os)、epoll(linux kenel 2.6+)、rtsig(实时信号)或/dev/poll（一种类似select的模式，底层实现与SELECT基本相同，都是采用轮询的方法），SELECT模式将是默认安装模式

        --with-poll_module(--without-poll_module) #允许或不允许开启POLL模式，如果没有合适的模式，比如：kqueue（sun os）、epoll（liunx kernel 2.6+），则开启该模式

        --with-http_ssl_module #开启HTTP SSL模块，使NGINX可以支持HTTPS请求。这个模块需要已经安装了OPENSSL，在DEBIAN上是libssl

        --with-http_realip_module #启用 ngx_http_realip_module

        --with-http_addition_module #启用 ngx_http_addition_module

        --with-http_sub_module #启用 ngx_http_sub_module

        --with-http_dav_module #启用 ngx_http_dav_module

        --with-http_flv_module #启用 ngx_http_flv_module

        --with-http_stub_status_module #启用 "server status" 页

        --without-http_charset_module #禁用 ngx_http_charset_module

        --without-http_gzip_module #禁用 ngx_http_gzip_module. 如果启用，需要 zlib 。

        --without-http_ssi_module #禁用 ngx_http_ssi_module

        --without-http_userid_module #禁用 ngx_http_userid_module

        --without-http_access_module #禁用 ngx_http_access_module

        --without-http_auth_basic_module #禁用 ngx_http_auth_basic_module
        
        --without-http_autoindex_module #禁用 ngx_http_autoindex_module

        --without-http_geo_module #禁用 ngx_http_geo_module

        --without-http_map_module #禁用 ngx_http_map_module

        --without-http_referer_module #禁用 ngx_http_referer_module

        --without-http_rewrite_module #禁用 ngx_http_rewrite_module. 如果启用需要 PCRE 。

        --without-http_proxy_module #禁用 ngx_http_proxy_module

        --without-http_fastcgi_module #禁用 ngx_http_fastcgi_module

        --without-http_memcached_module #禁用 ngx_http_memcached_module

        --without-http_limit_zone_module #禁用 ngx_http_limit_zone_module

        --without-http_empty_gif_module #禁用 ngx_http_empty_gif_module

        --without-http_browser_module #禁用 ngx_http_browser_module

        --without-http_upstream_ip_hash_module #禁用 ngx_http_upstream_ip_hash_module

        --with-http_perl_module #启用 ngx_http_perl_module

        --with-perl_modules_path=PATH #指定 perl 模块的路径

        --with-perl=PATH #指定 perl 执行文件的路径

        --http-log-path=PATH #指定http默认访问日志的路径

        --http-client-body-temp-path=PATH #指定http客户端请求缓存文件存放目录的路径

        --http-proxy-temp-path=PATH #指定http反向代理缓存文件存放目录的路径

        --http-fastcgi-temp-path=PATH #指定http FastCGI缓存文件存放目录的路径

        --without-http #禁用 HTTP server

        --with-mail #启用 IMAP4/POP3/SMTP 代理模块

        --with-mail_ssl_module #启用 ngx_mail_ssl_module

        --with-cc=PATH #指定 C 编译器的路径

        --with-cpp=PATH #指定 C 预处理器的路径

        --with-cc-opt=OPTIONS #设置C编译器的额外选项

        --with-ld-opt=OPTIONS #设置链接的额外选项

        --with-cpu-opt=CPU #为特定的 CPU 编译，有效的值包括：pentium, pentiumpro, pentium3, pentium4, athlon, opteron, amd64, sparc32, sparc64, ppc64

        --without-pcre #禁止 PCRE 库的使用。同时也会禁止 HTTP rewrite 模块。在 "location" 配置指令中的正则表达式也需要 PCRE 

        --with-pcre=DIR #指定 PCRE 库的源代码的路径

        --with-pcre-opt=OPTIONS #设置PCRE的额外编译选项

        --with-md5=DIR #使用MD5汇编源码

        --with-md5-opt=OPTIONS #设置MD5库的额外编译选项

        --with-md5-asm #使用MD5汇编源码

        --with-sha1=DIR #设置sha1库的源代码路径

        --with-sha1-opt=OPTIONS #设置sha1库的额外编译选项

        --with-sha1-asm #使用sha1汇编源码

        --with-zlib=DIR #设置zlib库的源代码路径

        --with-zlib-opt=OPTIONS #设置zlib库的额外编译选项

        --with-zlib-asm=CPU #zlib针对CPU的优化，合法的值是: pentium, pentiumpro

        --with-openssl=DIR #设置OpenSSL库的源代码路径 

        --with-openssl-opt=OPTIONS #设置OpenSSL库的额外编译选项

        --with-debug #启用调试日志

        --add-module=PATH #添加一个在指定路径中能够找到的第三方模块
        

在不同版本间，选项可能会有些许变化，请总是使用./configure --help命令来检查当前的选项列表。
        
测试
^^^^^^^^^^^^^^^^^^^^^^^^

        将Nginx conf文件的server block部分的配置如下：        
        
.. code:: c

    server {
        listen 80;
        server_name localhost;

        location / {
            root html;
            index index.html index.htm;
        }

        # redirect server error pages to the static page /50x.html
        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root html;
        }
    }

    
用户可以通过访问“http://localhost:80/index.html”页面来查看Nginx的欢迎页面。


Nginx在Windows环境下查看nginx进程
^^^^^^^^^^^^^^^^^^^^^^^^

        用户还可以通过命令行运行tasklist命令来查看nginx进程：
.. code:: c

        C:\>tasklist /fi "imagename eq nginx.exe"

        映像名称 PID 会话名 会话# 内存使用
        ========================= ======== ================ =========== ============
        nginx.exe 463024 Console 1 5,036 K
        nginx.exe 462960 Console 1 5,280 K  

        
如果nginx没有启动或没有得到预期展示页面，可查看error.log文件以查看失败原因。如果日志文件不存在，可在Windows事件日志中查看。

Nginx在Linux环境下查看nginx进程
^^^^^^^^^^^^^^^^^^^^^^^^  
        用户可以通过执行ps/top命令来查看nginx进程：
.. code:: c        
        
        ps aux|grep nginx
        admin 24913 0.0 0.0 58596 1048 ? Ss Feb27 0:00 nginx: master process ./nginx
        admin 24914 0.0 0.0 72772 5420 ? S Feb27 0:03 nginx: worker process


同上，如果nginx没有启动或者没有得到预期展示页面，可以查看error.log文件或调试来查看失败原因。



  
C.2 调试
+++++++++++++++++++++++++++++++++++++



C.3 debug point
+++++++++++++++



C.4 使用gdb
+++++++++++++



C.5 调试日志
++++++++++++++++



C.6 单元测试
++++++++++++++++



C.7 功能测试
++++++++++++++++



C.8 性能测试
++++++++++++++++



