nginx的请求处理阶段 (30%)
=======================================



接收请求流程 (99%)
-----------------------



http请求格式简介 (99%)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
首先介绍一下rfc2616中定义的http请求基本格式：

.. code:: c

    Request = Request-Line 
              * (( general-header         
                 | request-header          
                 | entity-header ) CRLF)  
              CRLF
              [ message-body ]

第一行是请求行（request line），用来说明请求方法，要访问的资源以及所使用的HTTP版本：

.. code:: c

    Request-Line   = Method SP Request-URI SP HTTP-Version CRLF

请求方法（Method）的定义如下，其中最常用的是GET，POST方法：

.. code:: c

    Method = "OPTIONS" 
    | "GET" 
    | "HEAD" 
    | "POST" 
    | "PUT" 
    | "DELETE" 
    | "TRACE" 
    | "CONNECT" 
    | extension-method 
    extension-method = token

要访问的资源由统一资源地位符URI(Uniform Resource Identifier)确定，它的一个比较通用的组成格式（rfc2396）如下：

.. code:: c

    <scheme>://<authority><path>?<query> 

一般来说根据请求方法（Method）的不同，请求URI的格式会有所不同，通常只需写出path和query部分。

http版本(version)定义如下，现在用的一般为1.0和1.1版本：

.. code:: c

    HTTP/<major>.<minor>

请求行的下一行则是请求头，rfc2616中定义了3种不同类型的请求头，分别为general-header，request-header和entity-header，每种类型rfc中都定义了一些通用的头，其中entity-header类型可以包含自定义的头。


请求头读取 (99%)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

这一节介绍nginx中请求头的解析，nginx的请求处理流程中，会涉及到2个非常重要的数据结构，ngx_connection_t和ngx_http_request_t，分别用来表示连接和请求，这2个数据结构在本书的前篇中已经做了比较详细的介绍，没有印象的读者可以翻回去复习一下，整个请求处理流程从头到尾，对应着这2个数据结构的分配，初始化，使用，重用和销毁。

nginx在初始化阶段，具体是在init process阶段的ngx_event_process_init函数中会为每一个监听套接字分配一个连接结构（ngx_connection_t），并将该连接结构的读事件成员（read）的事件处理函数设置为ngx_event_accept，并且如果没有使用accept互斥锁的话，在这个函数中会将该读事件挂载到nginx的事件处理模型上（poll或者epoll等），反之则会等到init process阶段结束，在工作进程的事件处理循环中，某个进程抢到了accept锁才能挂载该读事件。

.. code:: c

    static ngx_int_t
    ngx_event_process_init(ngx_cycle_t *cycle)
    {
        ...

        /* 初始化用来管理所有定时器的红黑树 */
        if (ngx_event_timer_init(cycle->log) == NGX_ERROR) {
            return NGX_ERROR;
        }
        /* 初始化事件模型 */
        for (m = 0; ngx_modules[m]; m++) {
            if (ngx_modules[m]->type != NGX_EVENT_MODULE) {
                continue;
            }

            if (ngx_modules[m]->ctx_index != ecf->use) {
                continue;
            }

            module = ngx_modules[m]->ctx;

            if (module->actions.init(cycle, ngx_timer_resolution) != NGX_OK) {
                /* fatal */
                exit(2);
            }

            break;
        }

        ...

        /* for each listening socket */
        /* 为每个监听套接字分配一个连接结构 */
        ls = cycle->listening.elts;
        for (i = 0; i < cycle->listening.nelts; i++) {

            c = ngx_get_connection(ls[i].fd, cycle->log);

            if (c == NULL) {
                return NGX_ERROR;
            }

            c->log = &ls[i].log;

            c->listening = &ls[i];
            ls[i].connection = c;

            rev = c->read;

            rev->log = c->log;
            /* 标识此读事件为新请求连接事件 */
            rev->accept = 1;

            ...

    #if (NGX_WIN32)

            /* windows环境下不做分析，但原理类似 */

    #else
            /* 将读事件结构的处理函数设置为ngx_event_accept */
            rev->handler = ngx_event_accept;
            /* 如果使用accept锁的话，要在后面抢到锁才能将监听句柄挂载上事件处理模型上 */
            if (ngx_use_accept_mutex) {
                continue;
            }
            /* 否则，将该监听句柄直接挂载上事件处理模型 */
            if (ngx_event_flags & NGX_USE_RTSIG_EVENT) {
                if (ngx_add_conn(c) == NGX_ERROR) {
                    return NGX_ERROR;
                }

            } else {
                if (ngx_add_event(rev, NGX_READ_EVENT, 0) == NGX_ERROR) {
                    return NGX_ERROR;
                }
            }

    #endif

        }

        return NGX_OK;
    }

当一个工作进程在某个时刻将监听事件挂载上事件处理模型之后，nginx就可以正式的接收并处理客户端过来的请求了。这时如果有一个用户在浏览器的地址栏内输入一个域名，并且域名解析服务器将该域名解析到一台由nginx监听的服务器上，nginx的事件处理模型接收到这个读事件之后，会交给之前注册好的事件处理函数ngx_event_accept来处理。

在ngx_event_accept函数中，nginx调用accept函数，从已连接队列得到一个连接以及对应的套接字，接着分配一个连接结构（ngx_connection_t），并将新得到的套接字保存在该连接结构中，这里还会做一些基本的连接初始化工作：

1, 首先给该连接分配一个内存池，初始大小默认为256字节，可通过connection_pool_size指令设置；

2, 分配日志结构，并保存在其中，以便后续的日志系统使用；

3, 初始化连接相应的io收发函数，具体的io收发函数和使用的事件模型及操作系统相关；

4, 分配一个套接口地址（sockaddr），并将accept得到的对端地址拷贝在其中，保存在sockaddr字段；

5, 将本地套接口地址保存在local_sockaddr字段，因为这个值是从监听结构ngx_listening_t中可得，而监听结构中保存的只是配置文件中设置的监听地址，但是配置的监听地址可能是通配符*，即监听在所有的地址上，所以连接中保存的这个值最终可能还会变动，会被确定为真正的接收地址；

6, 将连接的写事件设置为已就绪，即设置ready为1，nginx默认连接第一次为可写；

7, 如果监听套接字设置了TCP_DEFER_ACCEPT属性，则表示该连接上已经有数据包过来，于是设置读事件为就绪；

8, 将sockaddr字段保存的对端地址格式化为可读字符串，并保存在addr_text字段；

最后调用ngx_http_init_connection函数初始化该连接结构的其他部分。

ngx_http_init_connection函数最重要的工作是初始化读写事件的处理函数：将该连接结构的写事件的处理函数设置为ngx_http_empty_handler，这个事件处理函数不会做任何操作，实际上nginx默认连接第一次可写，不会挂载写事件，如果有数据需要发送，nginx会直接写到这个连接，只有在发生一次写不完的情况下，才会挂载写事件到事件模型上，并设置真正的写事件处理函数，这里后面的章节还会做详细介绍；读事件的处理函数设置为ngx_http_init_request，此时如果该连接上已经有数据过来（设置了deferred accept)，则会直接调用ngx_http_init_request函数来处理该请求，反之则设置一个定时器并在事件处理模型上挂载一个读事件，等待数据到来或者超时。当然这里不管是已经有数据到来，或者需要等待数据到来，又或者等待超时，最终都会进入读事件的处理函数-ngx_http_init_request。

ngx_http_init_request函数主要工作即是初始化请求，由于它是一个事件处理函数，它只有唯一一个ngx_event_t \*类型的参数，ngx_event_t 结构在nginx中表示一个事件，事件处理的上下文类似于一个中断处理的上下文，为了在这个上下文得到相关的信息，nginx中一般会将连接结构的引用保存在事件结构的data字段，请求结构的引用则保存在连接结构的data字段，这样在事件处理函数中可以方便的得到对应的连接结构和请求结构。进入函数内部看一下，首先判断该事件是否是超时事件，如果是的话直接关闭连接并返回；反之则是指之前accept的连接上有请求过来需要处理。

ngx_http_init_request函数首先在连接的内存池中为该请求分配一个ngx_http_request_t结构，这个结构将用来保存该请求所有的信息。分配完之后，这个结构的引用会被包存在连接的hc成员的request字段，以便于在长连接或pipelined请求中复用该请求结构。在这个函数中，nginx根据该请求的接收端口和地址找到一个默认虚拟服务器配置（listen指令的default_server属性用来标识一个默认虚拟服务器，否则监听在相同端口和地址的多个虚拟服务器，其中第一个定义的则为默认）。

nginx配置文件中可以设置多个监听在不同端口和地址的虚拟服务器（每个server块对应一个虚拟服务器），另外还根据域名（server_name指令可以配置该虚拟服务器对应的域名）来区分监听在相同端口和地址的虚拟服务器，每个虚拟服务器可以拥有不同的配置内容，而这些配置内容决定了nginx在接收到一个请求之后如何处理该请求。找到之后，相应的配置被保存在该请求对应的ngx_http_request_t结构中。注意这里根据端口和地址找到的默认配置只是临时使用一下，最终nginx会根据域名找到真正的虚拟服务器配置，随后的初始化工作还包括：

1, 将连接的读事件的处理函数设置为ngx_http_process_request_line函数，这个函数用来解析请求行，将请求的read_event_handler设置为ngx_http_block_reading函数，这个函数实际上什么都不做（当然在事件模型设置为水平触发时，唯一做的事情就是将事件从事件模型监听列表中删除，防止该事件一直被触发），后面会说到这里为什么会将read_event_handler设置为此函数；

2, 为这个请求分配一个缓冲区用来保存它的请求头，地址保存在header_in字段，默认大小为1024个字节，可以使用client_header_buffer_size指令修改，这里需要注意一下，nginx用来保存请求头的缓冲区是在该请求所在连接的内存池中分配，而且会将地址保存一份在连接的buffer字段中，这样做的目的也是为了给该连接的下一次请求重用这个缓冲区，另外如果客户端发过来的请求头大于1024个字节，nginx会重新分配更大的缓存区，默认用于大请求的头的缓冲区最大为8K，最多4个，这2个值可以用large_client_header_buffers指令设置，后面还会说到请求行和一个请求头都不能超过一个最大缓冲区的大小；

3, 为这个请求分配一个内存池，后续所有与该请求相关的内存分配一般都会使用该内存池，默认大小为4096个字节，可以使用request_pool_size指令修改；

4, 为这个请求分配响应头链表，初始大小为20；

5, 创建所有模块的上下文ctx指针数组，变量数据；

6, 将该请求的main字段设置为它本身，表示这是一个主请求，nginx中对应的还有子请求概念，后面的章节会做详细的介绍；

7, 将该请求的count字段设置为1，count字段表示请求的引用计数；

8, 将当前时间保存在start_sec和start_msec字段，这个时间是该请求的起始时刻，将被用来计算一个请求的处理时间（request time），nginx使用的这个起始点和apache略有差别，nginx中请求的起始点是接收到客户端的第一个数据包的事件开始，而apache则是接收到客户端的整个request line后开始算起；

9, 初始化请求的其他字段，比如将uri_changes设置为11，表示最多可以将该请求的uri改写10次，subrequests被设置为201，表示一个请求最多可以发起200个子请求；

做完所有这些初始化工作之后，ngx_http_init_request函数会调用读事件的处理函数来真正的解析客户端发过来的数据，也就是会进入ngx_http_process_request_line函数中处理。

解析请求行 (99%)
+++++++++++++++++++++

ngx_http_process_request_line函数的主要作用即是解析请求行，同样由于涉及到网络IO操作，即使是很短的一行请求行可能也不能被一次读完，所以在之前的ngx_http_init_request函数中，ngx_http_process_request_line函数被设置为读事件的处理函数，它也只拥有一个唯一的ngx_event_t \*类型参数，并且在函数的开头，同样需要判断是否是超时事件，如果是的话，则关闭这个请求和连接；否则开始正常的解析流程。先调用ngx_http_read_request_header函数读取数据。

由于可能多次进入ngx_http_process_request_line函数，ngx_http_read_request_header函数首先检查请求的header_in指向的缓冲区内是否有数据，有的话直接返回；否则从连接读取数据并保存在请求的header_in指向的缓存区，而且只要缓冲区有空间的话，会一次尽可能多的读数据，读到多少返回多少；如果客户端暂时没有发任何数据过来，并返回NGX_AGAIN，返回之前会做2件事情：

1，设置一个定时器，时长默认为60s，可以通过指令client_header_timeout设置，如果定时事件到达之前没有任何可读事件，nginx将会关闭此请求；

2，调用ngx_handle_read_event函数处理一下读事件-如果该连接尚未在事件处理模型上挂载读事件，则将其挂载上；

如果客户端提前关闭了连接或者读取数据发生了其他错误，则给客户端返回一个400错误（当然这里并不保证客户端能够接收到响应数据，因为客户端可能都已经关闭了连接），最后函数返回NGX_ERROR；

如果ngx_http_read_request_header函数正常的读取到了数据，ngx_http_process_request_line函数将调用ngx_http_parse_request_line函数来解析，这个函数根据http协议规范中对请求行的定义实现了一个有限状态机，经过这个状态机，nginx会记录请求行中的请求方法（Method），请求uri以及http协议版本在缓冲区中的起始位置，在解析过程中还会记录一些其他有用的信息，以便后面的处理过程中使用。如果解析请求行的过程中没有产生任何问题，该函数会返回NGX_OK；如果请求行不满足协议规范，该函数会立即终止解析过程，并返回相应错误号；如果缓冲区数据不够，该函数返回NGX_AGAIN。

在整个解析http请求的状态机中始终遵循着两条重要的原则：减少内存拷贝和回溯。

内存拷贝是一个相对比较昂贵的操作，大量的内存拷贝会带来较低的运行时效率。nginx在需要做内存拷贝的地方尽量只拷贝内存的起始和结束地址而不是内存本身，这样做的话仅仅只需要两个赋值操作而已，大大降低了开销，当然这样带来的影响是后续的操作不能修改内存本身，如果修改的话，会影响到所有引用到该内存区间的地方，所以必须很小心的管理，必要的时候需要拷贝一份。

这里不得不提到nginx中最能体现这一思想的数据结构，ngx_buf_t，它用来表示nginx中的缓存，在很多情况下，只需要将一块内存的起始地址和结束地址分别保存在它的pos和last成员中，再将它的memory标志置1，即可表示一块不能修改的内存区间，在另外的需要一块能够修改的缓存的情形中，则必须分配一块所需大小的内存并保存其起始地址，再将ngx_bug_t的temprary标志置1，表示这是一块能够被修改的内存区域。

再回到ngx_http_process_request_line函数中，如果ngx_http_parse_request_line函数返回了错误，则直接给客户端返回400错误；
如果返回NGX_AGAIN，则需要判断一下是否是由于缓冲区空间不够，还是已读数据不够。如果是缓冲区大小不够了，nginx会调用ngx_http_alloc_large_header_buffer函数来分配另一块大缓冲区，如果大缓冲区还不够装下整个请求行，nginx则会返回414错误给客户端，否则分配了更大的缓冲区并拷贝之前的数据之后，继续调用ngx_http_read_request_header函数读取数据来进入请求行自动机处理，直到请求行解析结束；

如果返回了NGX_OK，则表示请求行被正确的解析出来了，这时先记录好请求行的起始地址以及长度，并将请求uri的path和参数部分保存在请求结构的uri字段，请求方法起始位置和长度保存在method_name字段，http版本起始位置和长度记录在http_protocol字段。还要从uri中解析出参数以及请求资源的拓展名，分别保存在args和exten字段。接下来将要解析请求头，将在下一小节中接着介绍。

解析请求头 (99%)
+++++++++++++++++++++++

在ngx_http_process_request_line函数中，解析完请求行之后，如果请求行的uri里面包含了域名部分，则将其保存在请求结构的headers_in成员的server字段，headers_in用来保存所有请求头，它的类型为ngx_http_headers_in_t：


.. code:: c

    typedef struct {
        ngx_list_t                        headers;

        ngx_table_elt_t                  *host;
        ngx_table_elt_t                  *connection;
        ngx_table_elt_t                  *if_modified_since;
        ngx_table_elt_t                  *if_unmodified_since;
        ngx_table_elt_t                  *user_agent;
        ngx_table_elt_t                  *referer;
        ngx_table_elt_t                  *content_length;
        ngx_table_elt_t                  *content_type;

        ngx_table_elt_t                  *range;
        ngx_table_elt_t                  *if_range;

        ngx_table_elt_t                  *transfer_encoding;
        ngx_table_elt_t                  *expect;

    #if (NGX_HTTP_GZIP)
        ngx_table_elt_t                  *accept_encoding;
        ngx_table_elt_t                  *via;
    #endif

        ngx_table_elt_t                  *authorization;

        ngx_table_elt_t                  *keep_alive;

    #if (NGX_HTTP_PROXY || NGX_HTTP_REALIP || NGX_HTTP_GEO)
        ngx_table_elt_t                  *x_forwarded_for;
    #endif

    #if (NGX_HTTP_REALIP)
        ngx_table_elt_t                  *x_real_ip;
    #endif

    #if (NGX_HTTP_HEADERS)
        ngx_table_elt_t                  *accept;
        ngx_table_elt_t                  *accept_language;
    #endif

    #if (NGX_HTTP_DAV)
        ngx_table_elt_t                  *depth;
        ngx_table_elt_t                  *destination;
        ngx_table_elt_t                  *overwrite;
        ngx_table_elt_t                  *date;
    #endif

        ngx_str_t                         user;
        ngx_str_t                         passwd;

        ngx_array_t                       cookies;

        ngx_str_t                         server;
        off_t                             content_length_n;
        time_t                            keep_alive_n;

        unsigned                          connection_type:2;
        unsigned                          msie:1;
        unsigned                          msie6:1;
        unsigned                          opera:1;
        unsigned                          gecko:1;
        unsigned                          chrome:1;
        unsigned                          safari:1;
        unsigned                          konqueror:1;
    } ngx_http_headers_in_t;

接着，该函数会检查进来的请求是否使用的是http0.9，如果是的话则使用从请求行里得到的域名，调用ngx_http_find_virtual_server（）函数来查找用来处理该请求的虚拟服务器配置，之前通过端口和地址找到的默认配置不再使用，找到相应的配置之后，则直接调用ngx_http_process_request（）函数处理该请求，因为http0.9是最原始的http协议，它里面没有定义任何请求头，显然就不需要读取请求头的操作。

.. code:: c

            if (r->host_start && r->host_end) {

                host = r->host_start;
                n = ngx_http_validate_host(r, &host,
                                           r->host_end - r->host_start, 0);

                if (n == 0) {
                    ngx_log_error(NGX_LOG_INFO, c->log, 0,
                                  "client sent invalid host in request line");
                    ngx_http_finalize_request(r, NGX_HTTP_BAD_REQUEST);
                    return;
                }

                if (n < 0) {
                    ngx_http_close_request(r, NGX_HTTP_INTERNAL_SERVER_ERROR);
                    return;
                }

                r->headers_in.server.len = n;
                r->headers_in.server.data = host;
            }

            if (r->http_version < NGX_HTTP_VERSION_10) {

                if (ngx_http_find_virtual_server(r, r->headers_in.server.data,
                                                 r->headers_in.server.len)
                    == NGX_ERROR)
                {
                    ngx_http_close_request(r, NGX_HTTP_INTERNAL_SERVER_ERROR);
                    return;
                }

                ngx_http_process_request(r);
                return;
            }

当然，如果是1.0或者更新的http协议，接下来要做的就是读取请求头了，首先nginx会为请求头分配空间，ngx_http_headers_in_t结构的headers字段为一个链表结构，它被用来保存所有请求头，初始为它分配了20个节点，每个节点的类型为ngx_table_elt_t，保存请求头的name/value值对，还可以看到ngx_http_headers_in_t结构有很多类型为ngx_table_elt_t*的指针成员，而且从它们的命名可以看出是一些常见的请求头名字，nginx对这些常用的请求头在ngx_http_headers_in_t结构里面保存了一份引用，后续需要使用的话，可以直接通过这些成员得到，另外也事先为cookie头分配了2个元素的数组空间，做完这些内存准备工作之后，该请求对应的读事件结构的处理函数被设置为ngx_http_process_request_headers，并随后马上调用了该函数。

.. code:: c

            if (ngx_list_init(&r->headers_in.headers, r->pool, 20,
                              sizeof(ngx_table_elt_t))
                != NGX_OK)
            {
                ngx_http_close_request(r, NGX_HTTP_INTERNAL_SERVER_ERROR);
                return;
            }


            if (ngx_array_init(&r->headers_in.cookies, r->pool, 2,
                               sizeof(ngx_table_elt_t *))
                != NGX_OK)
            {
                ngx_http_close_request(r, NGX_HTTP_INTERNAL_SERVER_ERROR);
                return;
            }

            c->log->action = "reading client request headers";

            rev->handler = ngx_http_process_request_headers;
            ngx_http_process_request_headers(rev);

ngx_http_process_request_headers函数循环的读取所有的请求头，并保存和初始化和请求头相关的结构，下面详细分析一下该函数：

因为nginx对读取请求头有超时限制，ngx_http_process_request_headers函数作为读事件处理函数，一并处理了超时事件，如果读超时了，nginx直接给该请求返回408错误：

.. code:: c

   if (rev->timedout) {
        ngx_log_error(NGX_LOG_INFO, c->log, NGX_ETIMEDOUT, "client timed out");
        c->timedout = 1;
        ngx_http_close_request(r, NGX_HTTP_REQUEST_TIME_OUT);
        return;
    }

读取和解析请求头的逻辑和处理请求行差不多，总的流程也是循环的调用ngx_http_read_request_header（）函数读取数据，然后再调用一个解析函数来从读取的数据中解析请求头，直到解析完所有请求头，或者发生解析错误为主。当然由于涉及到网络io，这个流程可能发生在多个io事件的上下文中。

接着来细看该函数，先调用了ngx_http_read_request_header（）函数读取数据，如果当前连接并没有数据过来，再直接返回，等待下一次读事件到来，如果读到了一些数据则调用ngx_http_parse_header_line（）函数来解析，同样的该解析函数实现为一个有限状态机，逻辑很简单，只是根据http协议来解析请求头，每次调用该函数最多解析出一个请求头，该函数返回4种不同返回值，表示不同解析结果：

1，返回NGX_OK，表示解析出了一行请求头，这时还要判断解析出的请求头名字里面是否有非法字符，名字里面合法的字符包括字母，数字和连字符（-），另外如果设置了underscores_in_headers指令为on，则下划线也是合法字符，但是nginx默认下划线不合法，当请求头里面包含了非法的字符，nginx默认只是忽略这一行请求头；如果一切都正常，nginx会将该请求头及请求头名字的hash值保存在请求结构体的headers_in成员的headers链表,而且对于一些常见的请求头，如Host，Connection，nginx采用了类似于配置指令的方式，事先给这些请求头分配了一个处理函数，当解析出一个请求头时，会检查该请求头是否有设置处理函数，有的话则调用之，nginx所有有处理函数的请求头都记录在ngx_http_headers_in全局数组中：

.. code:: c

    typedef struct {
        ngx_str_t                         name;
        ngx_uint_t                        offset;
        ngx_http_header_handler_pt        handler;
    } ngx_http_header_t;

    ngx_http_header_t  ngx_http_headers_in[] = {
        { ngx_string("Host"), offsetof(ngx_http_headers_in_t, host),
                     ngx_http_process_host },

        { ngx_string("Connection"), offsetof(ngx_http_headers_in_t, connection),
                     ngx_http_process_connection },

        { ngx_string("If-Modified-Since"),
                     offsetof(ngx_http_headers_in_t, if_modified_since),
                     ngx_http_process_unique_header_line },

        { ngx_string("If-Unmodified-Since"),
                     offsetof(ngx_http_headers_in_t, if_unmodified_since),
                     ngx_http_process_unique_header_line },

        { ngx_string("User-Agent"), offsetof(ngx_http_headers_in_t, user_agent),
                     ngx_http_process_user_agent },

        { ngx_string("Referer"), offsetof(ngx_http_headers_in_t, referer),
                     ngx_http_process_header_line },

        { ngx_string("Content-Length"),
                     offsetof(ngx_http_headers_in_t, content_length),
                     ngx_http_process_unique_header_line },

        { ngx_string("Content-Type"),
                     offsetof(ngx_http_headers_in_t, content_type),
                     ngx_http_process_header_line },

        { ngx_string("Range"), offsetof(ngx_http_headers_in_t, range),
                     ngx_http_process_header_line },

        { ngx_string("If-Range"),
                     offsetof(ngx_http_headers_in_t, if_range),
                     ngx_http_process_unique_header_line },

        { ngx_string("Transfer-Encoding"),
                     offsetof(ngx_http_headers_in_t, transfer_encoding),
                     ngx_http_process_header_line },

        { ngx_string("Expect"),
                     offsetof(ngx_http_headers_in_t, expect),
                     ngx_http_process_unique_header_line },

    #if (NGX_HTTP_GZIP)
        { ngx_string("Accept-Encoding"),
                     offsetof(ngx_http_headers_in_t, accept_encoding),
                     ngx_http_process_header_line },

        { ngx_string("Via"), offsetof(ngx_http_headers_in_t, via),
                     ngx_http_process_header_line },
    #endif

        { ngx_string("Authorization"),
                     offsetof(ngx_http_headers_in_t, authorization),
                     ngx_http_process_unique_header_line },

        { ngx_string("Keep-Alive"), offsetof(ngx_http_headers_in_t, keep_alive),
                     ngx_http_process_header_line },

    #if (NGX_HTTP_PROXY || NGX_HTTP_REALIP || NGX_HTTP_GEO)
        { ngx_string("X-Forwarded-For"),
                     offsetof(ngx_http_headers_in_t, x_forwarded_for),
                     ngx_http_process_header_line },
    #endif

    #if (NGX_HTTP_REALIP)
        { ngx_string("X-Real-IP"),
                     offsetof(ngx_http_headers_in_t, x_real_ip),
                     ngx_http_process_header_line },
    #endif

    #if (NGX_HTTP_HEADERS)
        { ngx_string("Accept"), offsetof(ngx_http_headers_in_t, accept),
                     ngx_http_process_header_line },

        { ngx_string("Accept-Language"),
                     offsetof(ngx_http_headers_in_t, accept_language),
                     ngx_http_process_header_line },
    #endif

    #if (NGX_HTTP_DAV)
        { ngx_string("Depth"), offsetof(ngx_http_headers_in_t, depth),
                     ngx_http_process_header_line },

        { ngx_string("Destination"), offsetof(ngx_http_headers_in_t, destination),
                     ngx_http_process_header_line },

        { ngx_string("Overwrite"), offsetof(ngx_http_headers_in_t, overwrite),
                     ngx_http_process_header_line },

        { ngx_string("Date"), offsetof(ngx_http_headers_in_t, date),
                     ngx_http_process_header_line },
    #endif

        { ngx_string("Cookie"), 0, ngx_http_process_cookie },

        { ngx_null_string, 0, NULL }
    };

ngx_http_headers_in数组当前包含了25个常用的请求头，每个请求头都设置了一个处理函数，其中一部分请求头设置的是公共处理函数，这里有2个公共处理函数，ngx_http_process_header_line和ngx_http_process_unique_header_line。
先来看一下处理函数的函数指针定义：

.. code:: c

    typedef ngx_int_t (*ngx_http_header_handler_pt)(ngx_http_request_t *r,
        ngx_table_elt_t *h, ngx_uint_t offset);

它有3个参数，r为对应的请求结构，h为指向该请求头在headers_in.headers链表中对应节点的指针，offset为该请求头对应字段在ngx_http_headers_in_t结构中的偏移。

再来看ngx_http_process_header_line函数：

.. code:: c

    static ngx_int_t
    ngx_http_process_header_line(ngx_http_request_t *r, ngx_table_elt_t *h,
        ngx_uint_t offset)
    {
        ngx_table_elt_t  **ph;

        ph = (ngx_table_elt_t **) ((char *) &r->headers_in + offset);

        if (*ph == NULL) {
            *ph = h;
        }

        return NGX_OK;
    }

这个函数只是简单将该请求头在ngx_http_headers_in_t结构中保存一份引用。ngx_http_process_unique_header_line功能类似，不同点在于该函数会检查这个请求头是否是重复的，如果是的话，则给该请求返回400错误。

ngx_http_headers_in数组中剩下的请求头都有自己特殊的处理函数，这些特殊的函数根据对应的请求头有一些特殊的处理，下面拿Host头的处理函数ngx_http_process_host做一下介绍：

.. code:: c

    static ngx_int_t
    ngx_http_process_host(ngx_http_request_t *r, ngx_table_elt_t *h,
        ngx_uint_t offset)
    {
        u_char   *host;
        ssize_t   len;

        if (r->headers_in.host == NULL) {
            r->headers_in.host = h;
        }

        host = h->value.data;
        len = ngx_http_validate_host(r, &host, h->value.len, 0);

        if (len == 0) {
            ngx_log_error(NGX_LOG_INFO, r->connection->log, 0,
                          "client sent invalid host header");
            ngx_http_finalize_request(r, NGX_HTTP_BAD_REQUEST);
            return NGX_ERROR;
        }

        if (len < 0) {
            ngx_http_close_request(r, NGX_HTTP_INTERNAL_SERVER_ERROR);
            return NGX_ERROR;
        }

        if (r->headers_in.server.len) {
            return NGX_OK;
        }

        r->headers_in.server.len = len;
        r->headers_in.server.data = host;

        return NGX_OK;
    }

此函数的目的也是保存Host头的快速引用，它会对Host头的值做一些合法性检查，并从中解析出域名，保存在headers_in.server字段，实际上前面在解析请求行时，headers_in.server可能已经被赋值为从请求行中解析出来的域名，根据http协议的规范，如果请求行中的uri带有域名的话，则域名以它为准，所以这里需检查一下headers_in.server是否为空，如果不为空则不需要再赋值。

其他请求头的特殊处理函数，不再做介绍，大致都是根据该请求头在http协议中规定的意义及其值设置请求的一些属性，必备后续使用。

对一个合法的请求头的处理大致为如上所述；

2，返回NGX_AGAIN，表示当前接收到的数据不够，一行请求头还未结束，需要继续下一轮循环。在下一轮循环中，nginx首先检查请求头缓冲区header_in是否已满，如够满了，则调用ngx_http_alloc_large_header_buffer（）函数分配更多缓冲区，下面分析一下ngx_http_alloc_large_header_buffer函数：

.. code:: c

    static ngx_int_t
    ngx_http_alloc_large_header_buffer(ngx_http_request_t *r,
        ngx_uint_t request_line)
    {
        u_char                    *old, *new;
        ngx_buf_t                 *b;
        ngx_http_connection_t     *hc;
        ngx_http_core_srv_conf_t  *cscf;

        ngx_log_debug0(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                       "http alloc large header buffer");

        /*
         * 在解析请求行阶段，如果客户端在发送请求行之前发送了大量回车换行符将
         * 缓冲区塞满了，针对这种情况，nginx只是简单的重置缓冲区，丢弃这些垃圾
         * 数据，不需要分配更大的内存。
         */
        if (request_line && r->state == 0) {

            /* the client fills up the buffer with "\r\n" */

            r->request_length += r->header_in->end - r->header_in->start;

            r->header_in->pos = r->header_in->start;
            r->header_in->last = r->header_in->start;

            return NGX_OK;
        }

        /* 保存请求行或者请求头在旧缓冲区中的起始地址 */
        old = request_line ? r->request_start : r->header_name_start;

        cscf = ngx_http_get_module_srv_conf(r, ngx_http_core_module);

        /* 如果一个大缓冲区还装不下请求行或者一个请求头，则返回错误 */
        if (r->state != 0
            && (size_t) (r->header_in->pos - old)
                                         >= cscf->large_client_header_buffers.size)
        {
            return NGX_DECLINED;
        }

        hc = r->http_connection;

        /* 首先在ngx_http_connection_t结构中查找是否有空闲缓冲区，有的话，直接取之 */
        if (hc->nfree) {
            b = hc->free[--hc->nfree];

            ngx_log_debug2(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                           "http large header free: %p %uz",
                           b->pos, b->end - b->last);

        /* 检查给该请求分配的请求头缓冲区个数是否已经超过限制，默认最大个数为4个 */
        } else if (hc->nbusy < cscf->large_client_header_buffers.num) {

            if (hc->busy == NULL) {
                hc->busy = ngx_palloc(r->connection->pool,
                      cscf->large_client_header_buffers.num * sizeof(ngx_buf_t *));
                if (hc->busy == NULL) {
                    return NGX_ERROR;
                }
            }

            /* 如果还没有达到最大分配数量，则分配一个新的大缓冲区 */
            b = ngx_create_temp_buf(r->connection->pool,
                                    cscf->large_client_header_buffers.size);
            if (b == NULL) {
                return NGX_ERROR;
            }

            ngx_log_debug2(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                           "http large header alloc: %p %uz",
                           b->pos, b->end - b->last);

        } else {
            /* 如果已经达到最大的分配限制，则返回错误 */
            return NGX_DECLINED;
        }

        /* 将从空闲队列取得的或者新分配的缓冲区加入已使用队列 */
        hc->busy[hc->nbusy++] = b;

        /*
         * 因为nginx中，所有的请求头的保存形式都是指针（起始和结束地址），
         * 所以一行完整的请求头必须放在连续的内存块中。如果旧的缓冲区不能
         * 再放下整行请求头，则分配新缓冲区，并从旧缓冲区拷贝已经读取的部分请求头，
         * 拷贝完之后，需要修改所有相关指针指向到新缓冲区。
         * status为0表示解析完一行请求头之后，缓冲区正好被用完，这种情况不需要拷贝
         */
        if (r->state == 0) {
            /*
             * r->state == 0 means that a header line was parsed successfully
             * and we do not need to copy incomplete header line and
             * to relocate the parser header pointers
             */

            r->request_length += r->header_in->end - r->header_in->start;

            r->header_in = b;

            return NGX_OK;
        }

        ngx_log_debug1(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                       "http large header copy: %d", r->header_in->pos - old);

        r->request_length += old - r->header_in->start;

        new = b->start;

        /* 拷贝旧缓冲区中不完整的请求头 */
        ngx_memcpy(new, old, r->header_in->pos - old);

        b->pos = new + (r->header_in->pos - old);
        b->last = new + (r->header_in->pos - old);

        /* 修改相应的指针指向新缓冲区 */
        if (request_line) {
            r->request_start = new;

            if (r->request_end) {
                r->request_end = new + (r->request_end - old);
            }

            r->method_end = new + (r->method_end - old);

            r->uri_start = new + (r->uri_start - old);
            r->uri_end = new + (r->uri_end - old);

            if (r->schema_start) {
                r->schema_start = new + (r->schema_start - old);
                r->schema_end = new + (r->schema_end - old);
            }

            if (r->host_start) {
                r->host_start = new + (r->host_start - old);
                if (r->host_end) {
                    r->host_end = new + (r->host_end - old);
                }
            }

            if (r->port_start) {
                r->port_start = new + (r->port_start - old);
                r->port_end = new + (r->port_end - old);
            }

            if (r->uri_ext) {
                r->uri_ext = new + (r->uri_ext - old);
            }

            if (r->args_start) {
                r->args_start = new + (r->args_start - old);
            }

            if (r->http_protocol.data) {
                r->http_protocol.data = new + (r->http_protocol.data - old);
            }

        } else {
            r->header_name_start = new;
            r->header_name_end = new + (r->header_name_end - old);
            r->header_start = new + (r->header_start - old);
            r->header_end = new + (r->header_end - old);
        }

        r->header_in = b;

        return NGX_OK;
    }

当ngx_http_alloc_large_header_buffer函数返回NGX_DECLINED时，表示客户端发送了一行过大的请求头，或者是整个请求头部超过了限制，nginx会返回494错误，注意到nginx在返回494错误之前将请求的lingering_close标识置为了1，这样做的目的是在返回响应之前丢弃掉客户端发过来的其他数据；

3，返回NGX_HTTP_PARSE_INVALID_HEADER，表示请求头解析过程中遇到错误，一般为客户端发送了不符合协议规范的头部，此时nginx返回400错误；

4，返回NGX_HTTP_PARSE_HEADER_DONE，表示所有请求头已经成功的解析，这时请求的状态被设置为NGX_HTTP_PROCESS_REQUEST_STATE，意味着结束了请求读取阶段，正式进入了请求处理阶段，但是实际上请求可能含有请求体，nginx在请求读取阶段并不会去读取请求体，这个工作交给了后续的请求处理阶段的模块，这样做的目的是nginx本身并不知道这些请求体是否有用，如果后续模块并不需要的话，一方面请求体一般较大，如果全部读取进内存，则白白耗费大量的内存空间，另一方面即使nginx将请求体写进磁盘，但是涉及到磁盘io，会耗费比较多时间。所以交由后续模块来决定读取还是丢弃请求体是最明智的办法。

读取完请求头之后，nginx调用了ngx_http_process_request_header（）函数，这个函数主要做了两个方面的事情，一是调用ngx_http_find_virtual_server（）函数查找虚拟服务器配置；二是对一些请求头做一些协议的检查。比如对那些使用http1.1协议但是却没有发送Host头的请求，nginx给这些请求返回400错误。还有nginx现在的版本并不支持chunked格式的输入，如果某些请求申明自己使用了chunked格式的输入（请求带有值为chunked的transfer_encoding头部)，nginx给这些请求返回411错误。等等。

最后调用ngx_http_process_request（）函数处理请求,至此，nginx请求头接收流程就介绍完毕。



请求体读取(100%)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

上节说到nginx核心本身不会主动读取请求体，这个工作是交给请求处理阶段的模块来做，但是nginx核心提供了ngx_http_read_client_request_body()接口来读取请求体，另外还提供了一个丢弃请求体的接口-ngx_http_discard_request_body()，在请求执行的各个阶段中，任何一个阶段的模块如果对请求体感兴趣或者希望丢掉客户端发过来的请求体，可以分别调用这两个接口来完成。这两个接口是nginx核心提供的处理请求体的标准接口，如果希望配置文件中一些请求体相关的指令（比如client_body_in_file_only，client_body_buffer_size等）能够预期工作，以及能够正常使用nginx内置的一些和请求体相关的变量（比如$request_body和$request_body_file），一般来说所有模块都必须调用这些接口来完成相应操作，如果需要自定义接口来处理请求体，也应尽量兼容nginx默认的行为。

读取请求体
+++++++++++++

请求体的读取一般发生在nginx的content handler中，一些nginx内置的模块，比如proxy模块，fastcgi模块，uwsgi模块等，这些模块的行为必须将客户端过来的请求体（如果有的话）以相应协议完整的转发到后端服务进程，所有的这些模块都是调用了ngx_http_read_client_request_body()接口来完成请求体读取。值得注意的是这些模块会把客户端的请求体完整的读取后才开始往后端转发数据。

由于内存的限制，ngx_http_read_client_request_body()接口读取的请求体会部分或者全部写入一个临时文件中，根据请求体的大小以及相关的指令配置，请求体可能完整放置在一块连续内存中，也可能分别放置在两块不同内存中，还可能全部存在一个临时文件中，最后还可能一部分在内存，剩余部分在临时文件中。下面先介绍一下和这些不同存储行为相关的指令\：

:client_body_buffer_size: 设置缓存请求体的buffer大小，默认为系统页大小的2倍，当请求体的大小超过此大小时，nginx会把请求体写入到临时文件中。可以根据业务需求设置合适的大小，尽量避免磁盘io操作;

:client_body_in_single_buffer: 指示是否将请求体完整的存储在一块连续的内存中，默认为off，如果此指令被设置为on，则nginx会保证请求体在不大于client_body_buffer_size设置的值时，被存放在一块连续的内存中，但超过大小时会被整个写入一个临时文件;

:client_body_in_file_only: 设置是否总是将请求体保存在临时文件中，默认为off，当此指定被设置为on时，即使客户端显式指示了请求体长度为0时，nginx还是会为请求创建一个临时文件。

接着介绍ngx_http_read_client_request_body()接口的实现，它的定义如下：

.. code:: c

    ngx_int_t
    ngx_http_read_client_request_body(ngx_http_request_t *r,
        ngx_http_client_body_handler_pt post_handler)

该接口有2个参数，第1个为指向请求结构的指针，第2个为一个函数指针，当请求体读完时，它会被调用。之前也说到根据nginx现有行为，模块逻辑会在请求体读完后执行，这个回调函数一般就是模块的逻辑处理函数。ngx_http_read_client_request_body()函数首先将参数r对应的主请求的引用加1，这样做的目的和该接口被调用的上下文有关，一般而言，模块是在content handler中调用此接口，一个典型的调用如下：

.. code:: c

    static ngx_int_t
    ngx_http_proxy_handler(ngx_http_request_t *r)
    {
        ...
        rc = ngx_http_read_client_request_body(r, ngx_http_upstream_init);


        if (rc >= NGX_HTTP_SPECIAL_RESPONSE) {
            return rc;
        }

        return NGX_DONE;
    }

上面的代码是在porxy模块的content handler，ngx_http_proxy_handler()中调用了ngx_http_read_client_request_body()函数，其中ngx_http_upstream_init()被作为回调函数传入进接口中，另外nginx中模块的content handler调用的上下文如下：

.. code:: c

    ngx_int_t
    ngx_http_core_content_phase(ngx_http_request_t *r,
        ngx_http_phase_handler_t *ph)
    {
        ...
        if (r->content_handler) {
            r->write_event_handler = ngx_http_request_empty_handler;
            ngx_http_finalize_request(r, r->content_handler(r));
            return NGX_OK;
        }
        ...
    }

上面的代码中，content handler调用之后，它的返回值作为参数调用了ngx_http_finalize_request()函数，在请求体没有被接收完全时，ngx_http_read_client_request_body()函数返回值为NGX_AGAIN，此时content handler，比如ngx_http_proxy_handler()会返回NGX_DONE，而NGX_DONE作为参数传给ngx_http_finalize_request()函数会导致主请求的引用计数减1，所以正好抵消了ngx_http_read_client_request_body()函数开头对主请求计数的加1。

接下来回到ngx_http_read_client_request_body()函数，它会检查该请求的请求体是否已经被读取或者被丢弃了，如果是的话，则直接调用回调函数并返回NGX_OK，这里实际上是为子请求检查，子请求是nginx中的一个概念，nginx中可以在当前请求中发起另外一个或多个全新的子请求来访问其他的location，关于子请求的具体介绍会在后面的章节作详细分析，一般而言子请求不需要自己去读取请求体。

函数接着调用ngx_http_test_expect()检查客户端是否发送了Expect: 100-continue头，是的话则给客户端回复"HTTP/1.1 100 Continue"，根据http 1.1协议，客户端可以发送一个Expect头来向服务器表明期望发送请求体，服务器如果允许客户端发送请求体，则会回复"HTTP/1.1 100 Continue"，客户端收到时，才会开始发送请求体。

接着继续为接收请求体做准备工作，分配一个ngx_http_request_body_t结构，并保存在r->request_body，这个结构用来保存请求体读取过程用到的缓存引用，临时文件引用，剩余请求体大小等信息，它的定义如下:

.. code:: c

    typedef struct {
        ngx_temp_file_t                  *temp_file;
        ngx_chain_t                      *bufs;
        ngx_buf_t                        *buf;
        off_t                             rest;
        ngx_chain_t                      *to_write;
        ngx_http_client_body_handler_pt   post_handler;
    } ngx_http_request_body_t;

:temp_file: 指向储存请求体的临时文件的指针；

:bufs: 指向保存请求体的链表头；

:buf: 指向当前用于保存请求体的内存缓存；

:rest: 当前剩余的请求体大小；

:post_handler: 保存传给ngx_http_read_client_request_body()函数的回调函数。

做好准备工作之后，函数开始检查请求是否带有content_length头，如果没有该头或者客户端发送了一个值为0的content_length头，表明没有请求体，这时直接调用回调函数并返回NGX_OK即可。当然如果client_body_in_file_only指令被设置为on，且content_length为0时，该函数在调用回调函数之前，会创建一个空的临时文件。

进入到函数下半部分，表明客户端请求确实表明了要发送请求体，该函数会先检查是否在读取请求头时预读了请求体，这里的检查是通过判断保存请求头的缓存(r->header_in)中是否还有未处理的数据。如果有预读数据，则分配一个ngx_buf_t结构，并将r->header_in中的预读数据保存在其中，并且如果r->header_in中还有剩余空间，并且能够容下剩余未读取的请求体，这些空间将被继续使用，而不用分配新的缓存，当然甚至如果请求体已经被整个预读了，则不需要继续处理了，此时调用回调函数后返回。

如果没有预读数据或者预读不完整，该函数会分配一块新的内存（除非r->header_in还有足够的剩余空间），另外如果request_body_in_single_buf指令被设置为no，则预读的数据会被拷贝进新开辟的内存块中，真正读取请求体的操作是在ngx_http_do_read_client_request_body()函数，该函数循环的读取请求体并保存在缓存中，如果缓存被写满了，其中的数据会被清空并写回到临时文件中。当然这里有可能不能一次将数据读到，该函数会挂载读事件并设置读事件handler为ngx_http_read_client_request_body_handler，另外nginx核心对两次请求体的读事件之间也做了超时设置，client_body_timeout指令可以设置这个超时时间，默认为60秒，如果下次读事件超时了，nginx会返回408给客户端。

最终读完请求体后，ngx_http_do_read_client_request_body()会根据配置，将请求体调整到预期的位置(内存或者文件)，所有情况下请求体都可以从r->request_body的bufs链表得到，该链表最多可能有2个节点，每个节点为一个buffer，但是这个buffer的内容可能是保存在内存中，也可能是保存在磁盘文件中。另外$request_body变量只在当请求体已经被读取并且是全部保存在内存中，才能取得相应的数据。

丢弃请求体
+++++++++++++

一个模块想要主动的丢弃客户端发过的请求体，可以调用nginx核心提供的ngx_http_discard_request_body()接口，主动丢弃的原因可能有很多种，如模块的业务逻辑压根不需要请求体 ，客户端发送了过大的请求体，另外为了兼容http1.1协议的pipeline请求，模块有义务主动丢弃不需要的请求体。总之为了保持良好的客户端兼容性，nginx必须主动丢弃无用的请求体。下面开始分析ngx_http_discard_request_body()函数：

.. code:: c

    ngx_int_t
    ngx_http_discard_request_body(ngx_http_request_t *r)
    {
        ssize_t       size;
        ngx_event_t  *rev;

        if (r != r->main || r->discard_body) {
            return NGX_OK;
        }

        if (ngx_http_test_expect(r) != NGX_OK) {
            return NGX_HTTP_INTERNAL_SERVER_ERROR;
        }

        rev = r->connection->read;

        ngx_log_debug0(NGX_LOG_DEBUG_HTTP, rev->log, 0, "http set discard body");

        if (rev->timer_set) {
            ngx_del_timer(rev);
        }

        if (r->headers_in.content_length_n <= 0 || r->request_body) {
            return NGX_OK;
        }

        size = r->header_in->last - r->header_in->pos;

        if (size) {
            if (r->headers_in.content_length_n > size) {
                r->header_in->pos += size;
                r->headers_in.content_length_n -= size;

            } else {
                r->header_in->pos += (size_t) r->headers_in.content_length_n;
                r->headers_in.content_length_n = 0;
                return NGX_OK;
            }
        }

        r->read_event_handler = ngx_http_discarded_request_body_handler;

        if (ngx_handle_read_event(rev, 0) != NGX_OK) {
            return NGX_HTTP_INTERNAL_SERVER_ERROR;
        }

        if (ngx_http_read_discarded_request_body(r) == NGX_OK) {
            r->lingering_close = 0;

        } else {
            r->count++;
            r->discard_body = 1;
        }

        return NGX_OK;
    }

由于函数不长，这里把它完整的列出来了，函数的开始同样先判断了不需要再做处理的情况：子请求不需要处理，已经调用过此函数的也不需要再处理。接着调用ngx_http_test_expect() 处理http1.1 expect的情况，根据http1.1的expect机制，如果客户端发送了expect头，而服务端不希望接收请求体时，必须返回417(Expectation Failed)错误。nginx并没有这样做，它只是简单的让客户端把请求体发送过来，然后丢弃掉。接下来，函数删掉了读事件上的定时器，因为这时本身就不需要请求体，所以也无所谓客户端发送的快还是慢了，当然后面还会讲到，当nginx已经处理完该请求但客户端还没有发送完无用的请求体时，nginx会在读事件上再挂上定时器。

客户端如果打算发送请求体，就必须发送content-length头，所以函数会检查请求头中的content-length头，同时还会查看其他地方是不是已经读取了请求体。如果确实有待处理的请求体，函数接着检查请求头buffer中预读的数据，预读的数据会直接被丢掉，当然如果请求体已经被全部预读，函数就直接返回了。

接下来，如果还有剩余的请求体未处理，该函数调用ngx_handle_read_event()在事件处理机制中挂载好读事件，并把读事件的处理函数设置为ngx_http_discarded_request_body_handler。做好这些准备之后，该函数最后调用ngx_http_read_discarded_request_body()接口读取客户端过来的请求体并丢弃。如果客户端并没有一次将请求体发过来，函数会返回，剩余的数据等到下一次读事件过来时，交给ngx_http_discarded_request_body_handler()来处理，这时，请求的discard_body将被设置为1用来标识这种情况。另外请求的引用数(count)也被加1，这样做的目的是客户端可能在nginx处理完请求之后仍未完整发送待发送的请求体，增加引用是防止nginx核心在处理完请求后直接释放了请求的相关资源。

ngx_http_read_discarded_request_body()函数非常简单，它循环的从链接中读取数据并丢弃，直到读完接收缓冲区的所有数据，如果请求体已经被读完了，该函数会设置读事件的处理函数为ngx_http_block_reading，这个函数仅仅删除水平触发的读事件，防止同一事件不断被触发。

最后看一下读事件的处理函数ngx_http_discarded_request_body_handler，这个函数每次读事件来时会被调用，先看一下它的源码：

.. code:: c

    void
    ngx_http_discarded_request_body_handler(ngx_http_request_t *r)
    {
        ...

        c = r->connection;
        rev = c->read;

        if (rev->timedout) {
            c->timedout = 1;
            c->error = 1;
            ngx_http_finalize_request(r, NGX_ERROR);
            return;
        }

        if (r->lingering_time) {
            timer = (ngx_msec_t) (r->lingering_time - ngx_time());

            if (timer <= 0) {
                r->discard_body = 0;
                r->lingering_close = 0;
                ngx_http_finalize_request(r, NGX_ERROR);
                return;
            }

        } else {
            timer = 0;
        }

        rc = ngx_http_read_discarded_request_body(r);

        if (rc == NGX_OK) {
            r->discard_body = 0;
            r->lingering_close = 0;
            ngx_http_finalize_request(r, NGX_DONE);
            return;
        }

        /* rc == NGX_AGAIN */

        if (ngx_handle_read_event(rev, 0) != NGX_OK) {
            c->error = 1;
            ngx_http_finalize_request(r, NGX_ERROR);
            return;
        }

        if (timer) {

            clcf = ngx_http_get_module_loc_conf(r, ngx_http_core_module);

            timer *= 1000;

            if (timer > clcf->lingering_timeout) {
                timer = clcf->lingering_timeout;
            }

            ngx_add_timer(rev, timer);
        }
    }

函数一开始就处理了读事件超时的情况，之前说到在ngx_http_discard_request_body()函数中已经删除了读事件的定时器，那么什么时候会设置定时器呢？答案就是在nginx已经处理完该请求，但是又没有完全将该请求的请求体丢弃的时候（客户端可能还没有发送过来），在ngx_http_finalize_connection()函数中，如果检查到还有未丢弃的请求体时，nginx会添加一个读事件定时器，它的时长为lingering_timeout指令所指定，默认为5秒，不过这个时间仅仅两次读事件之间的超时时间，等待请求体的总时长为lingering_time指令所指定，默认为30秒。这种情况中，该函数如果检测到超时事件则直接返回并断开连接。同样，还需要控制整个丢弃请求体的时长不能超过lingering_time设置的时间，如果超过了最大时长，也会直接返回并断开连接。

如果读事件发生在请求处理完之前，则不用处理超时事件，也不用设置定时器，函数只是简单的调用ngx_http_read_discarded_request_body()来读取并丢弃数据。


多阶段处理请求
--------------------------



find-config阶段
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



rewrite阶段
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



post-rewrite阶段
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



access阶段
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



post-access阶段
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



content阶段
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



log阶段
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



返回响应数据
-----------------------



header filter分析
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



body filter分析
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



finalize_request函数分析
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



特殊响应
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



chunked响应体
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



pipeline请求
-------------------



keepalive请求
--------------------



subrequest原理解析 (99%)
-----------------------------

子请求并不是http标准里面的概念，它是在当前请求中发起的一个新的请求，它拥有自己的ngx_http_request_t结构，uri和args。一般来说使用subrequest的效率可能会有些影响，因为它需要重新从server rewrite开始走一遍request处理的PHASE，但是它在某些情况下使用能带来方便，比较常用的是用subrequest来访问一个upstream的后端，并给它一个ngx_http_post_subrequest_t的回调handler，这样有点类似于一个异步的函数调用。对于从upstream返回的数据，subrequest允许根据创建时指定的flag，来决定由用户自己处理(回调handler中)还是由upstream模块直接发送到out put filter。简单的说一下subrequest的行为，nginx使用subrequest访问某个location，产生相应的数据，并插入到nginx输出链的相应位置（创建subrequest时的位置），下面用nginx代码内的addition模块(默认未编译进nginx核心，请使用--with-http_addition_module选项包含此模块)来举例说明一下：

.. code:: c

    location /main.htm {
        # content of main.htm: main
        add_before_body /hello.htm;
        add_after_body /world.htm;
    }
    location /hello.htm {
        #content of hello.htm: hello
    }
    location /world.htm {
        #content of world.htm: world
    }

访问/main.htm，将得到如下响应：

.. code:: c

    hello
    main
    world

上面的add_before_body指令发起一个subrequest来访问/hello.htm，并将产生的内容(hello)插入主请求响应体的开头，add_after_body指令发起一个subrequest访问/world.htm，并将产生的内容(world)附加在主请求响应体的结尾。addition模块是一个filter模块，但是subrequest既可以在phase模块中使用，也可以在filter模块中使用。

在进行源码解析之前，先来想想如果是我们自己要实现subrequest的上述行为，该如何来做？subrequest还可能有自己的subrequest，而且每个subrequest都不一定按照其创建的顺序来输出数据，所以简单的采用链表不好实现，于是进一步联想到可以采用树的结构来做，主请求即为根节点，每个节点可以有自己的子节点，遍历某节点表示处理某请求，自然的可以想到这里可能是用后根(序)遍历的方法，没错，实际上Igor采用树和链表结合的方式实现了subrequest的功能，但是由于节点（请求）产生数据的顺序不是固定按节点创建顺序(左->右)，而且可能分多次产生数据，不能简单的用后根(序)遍历。Igor使用了2个链表的结构来实现，第一个是每个请求都有的postponed链表，一般情况下每个链表节点保存了该请求的一个子请求，该链表节点定义如下：

.. code:: c

    struct ngx_http_postponed_request_s {
        ngx_http_request_t               *request;
        ngx_chain_t                      *out;
        ngx_http_postponed_request_t     *next;
    };

可以看到它有一个request字段，可以用来保存子请求，另外还有一个ngx_chain_t类型的out字段，实际上一个请求的postponed链表里面除了保存子请求的节点，还有保存该请求自己产生的数据的节点，数据保存在out字段；第二个是posted_requests链表，它挂载了当前需要遍历的请求（节点）， 该链表保存在主请求（根节点）的posted_requests字段，链表节点定义如下：

.. code:: c

    struct ngx_http_posted_request_s {
        ngx_http_request_t               *request;
        ngx_http_posted_request_t        *next;
    };

在ngx_http_run_posted_requests函数中会顺序的遍历主请求的posted_requests链表：

.. code:: c

    void
    ngx_http_run_posted_requests(ngx_connection_t *c)
    {
        ...
        for ( ;; ) {
            /* 连接已经断开，直接返回 */
            if (c->destroyed) {
                return;
            }

            r = c->data;
            /* 从posted_requests链表的队头开始遍历 */
            pr = r->main->posted_requests;

            if (pr == NULL) {
                return;
            }
          

            /* 从链表中移除即将要遍历的节点 */
            r->main->posted_requests = pr->next;
            /* 得到该节点中保存的请求 */
            r = pr->request;

            ctx = c->log->data;
            ctx->current_request = r;

            ngx_log_debug2(NGX_LOG_DEBUG_HTTP, c->log, 0,
                           "http posted request: \"%V?%V\"", &r->uri, &r->args);
            /* 遍历该节点（请求） */
            r->write_event_handler(r);
        }
    }

ngx_http_run_posted_requests函数的调用点后面会做说明。

了解了一些实现的原理，来看代码就简单多了，现在正式进行subrequest的源码解析， 首先来看一下创建subrequest的函数定义：

.. code:: c

    ngx_int_t
    ngx_http_subrequest(ngx_http_request_t *r,
        ngx_str_t *uri, ngx_str_t *args, ngx_http_request_t **psr,
        ngx_http_post_subrequest_t *ps, ngx_uint_t flags)

参数r为当前的请求，uri和args为新的要发起的uri和args，当然args可以为NULL，psr为指向一个ngx_http_request_t指针的指针，它的作用就是获得创建的子请求，ps的类型为ngx_http_post_subrequest_t，它的定义如下：

.. code:: c

    typedef struct {
        ngx_http_post_subrequest_pt       handler;
        void                             *data;
    } ngx_http_post_subrequest_t;

    typedef ngx_int_t (*ngx_http_post_subrequest_pt)(ngx_http_request_t *r,
        void *data, ngx_int_t rc);

它就是之前说到的回调handler，结构里面的handler类型为ngx_http_post_subrequest_pt，它是函数指针，data为传递给handler的额外参数。再来看一下ngx_http_subrequest函数的最后一个是flags，现在的源码中实际上只有2种类型的flag，分别为NGX_HTTP_SUBREQUEST_IN_MEMORY和NGX_HTTP_SUBREQUEST_WAITED，第一个就是指定文章开头说到的子请求的upstream处理数据的方式，第二个参数表示如果该子请求提前完成(按后序遍历的顺序)，是否设置将它的状态设为done，当设置该参数时，提前完成就会设置done，不设时，会让该子请求等待它之前的子请求处理完毕才会将状态设置为done。

进入ngx_http_subrequest函数内部看看：

.. code:: c

    {
        ...
        /* 解析flags， subrequest_in_memory在upstream模块解析完头部，
           发送body给downsstream时用到 */
        sr->subrequest_in_memory = (flags & NGX_HTTP_SUBREQUEST_IN_MEMORY) != 0;
        sr->waited = (flags & NGX_HTTP_SUBREQUEST_WAITED) != 0;

        sr->unparsed_uri = r->unparsed_uri;
        sr->method_name = ngx_http_core_get_method;
        sr->http_protocol = r->http_protocol;

        ngx_http_set_exten(sr);
        /* 主请求保存在main字段中 */
        sr->main = r->main;
        /* 父请求为当前请求 */   
        sr->parent = r;
        /* 保存回调handler及数据，在子请求执行完，将会调用 */
        sr->post_subrequest = ps;
        /* 读事件handler赋值为不做任何事的函数，因为子请求不用再读数据或者检查连接状态；
           写事件handler为ngx_http_handler，它会重走phase */
        sr->read_event_handler = ngx_http_request_empty_handler;
        sr->write_event_handler = ngx_http_handler;

        /* ngx_connection_s的data字段比较关键，它保存了当前可以向out chain输出数据的请求，
           具体意义后面会做详细介绍 */
        if (c->data == r && r->postponed == NULL) {
            c->data = sr;
        }
        /* 默认共享父请求的变量，当然你也可以根据需求在创建完子请求后，再创建子请求独立的变量集 */
        sr->variables = r->variables;

        sr->log_handler = r->log_handler;

        pr = ngx_palloc(r->pool, sizeof(ngx_http_postponed_request_t));
        if (pr == NULL) {
            return NGX_ERROR;
        }

        pr->request = sr;
        pr->out = NULL;
        pr->next = NULL;
        /* 把该子请求挂载在其父请求的postponed链表的队尾 */
        if (r->postponed) {
            for (p = r->postponed; p->next; p = p->next) { /* void */ }
            p->next = pr;

        } else {
            r->postponed = pr;
        }
        /* 子请求为内部请求，它可以访问internal类型的location */
        sr->internal = 1;
        /* 继承父请求的一些状态 */
        sr->discard_body = r->discard_body;
        sr->expect_tested = 1;
        sr->main_filter_need_in_memory = r->main_filter_need_in_memory;

        sr->uri_changes = NGX_HTTP_MAX_URI_CHANGES + 1;

        tp = ngx_timeofday();
        r->start_sec = tp->sec;
        r->start_msec = tp->msec;

        r->main->subrequests++;
        /* 增加主请求的引用数，这个字段主要是在ngx_http_finalize_request调用的一些结束请求和
           连接的函数中使用 */
        r->main->count++;

        *psr = sr;
        /* 将该子请求挂载在主请求的posted_requests链表队尾 */
        return ngx_http_post_request(sr, NULL);
    }

到这时，子请求创建完毕，一般来说子请求的创建都发生在某个请求的content handler或者某个filter内，从上面的函数可以看到子请求并没有马上被执行，只是被挂载在了主请求的posted_requests链表中，那它什么时候可以执行呢？之前说到posted_requests链表是在ngx_http_run_posted_requests函数中遍历，那么ngx_http_run_posted_requests函数又是在什么时候调用？它实际上是在某个请求的读（写）事件的handler中，执行完该请求相关的处理后被调用，比如主请求在走完一遍PHASE的时候会调用ngx_http_run_posted_requests，这时子请求得以运行。

这时实际还有1个问题需要解决，由于nginx是多进程，是不能够随意阻塞的（如果一个请求阻塞了当前进程，就相当于阻塞了这个进程accept到的所有其他请求，同时该进程也不能accept新请求），一个请求可能由于某些原因需要阻塞（比如访问io），nginx的做法是设置该请求的一些状态并在epoll中添加相应的事件，然后转去处理其他请求，等到该事件到来时再继续处理该请求，这样的行为就意味着一个请求可能需要多次执行机会才能完成，对于一个请求的多个子请求来说，意味着它们完成的先后顺序可能和它们创建的顺序是不一样的，所以必须有一种机制让提前完成的子请求保存它产生的数据，而不是直接输出到out chain，同时也能够让当前能够往out chain输出数据的请求及时的输出产生的数据。作者Igor采用ngx_connection_t中的data字段，以及一个body filter，即ngx_http_postpone_filter，还有ngx_http_finalize_request函数中的一些逻辑来解决这个问题。

下面用一个图来做说明，下图是某时刻某个主请求和它的所有子孙请求的树结构：

.. image:: http://tengine.taobao.org/book/_images/chapter-12-1.png
    :height:  273 px
    :width:   771 px
    :scale:   80 %
    :align:   center

图中的root节点即为主请求，它的postponed链表从左至右挂载了3个节点，SUB1是它的第一个子请求，DATA1是它产生的一段数据，SUB2是它的第2个子请求，而且这2个子请求分别有它们自己的子请求及数据。ngx_connection_t中的data字段保存的是当前可以往out chain发送数据的请求，文章开头说到发到客户端的数据必须按照子请求创建的顺序发送，这里即是按后序遍历的方法（SUB11->DATA11->SUB12->DATA12->(SUB1)->DATA1->SUB21->SUB22->(SUB2)->(ROOT)），上图中当前能够往客户端（out chain）发送数据的请求显然就是SUB11，如果SUB12提前执行完成，并产生数据DATA121，只要前面它还有节点未发送完毕，DATA121只能先挂载在SUB12的postponed链表下。这里还要注意一下的是c->data的设置，当SUB11执行完并且发送完数据之后，下一个将要发送的节点应该是DATA11，但是该节点实际上保存的是数据，而不是子请求，所以c->data这时应该指向的是拥有改数据节点的SUB1请求。

下面看下源码具体是怎样实现的，首先是ngx_http_postpone_filter函数：

.. code:: c

    static ngx_int_t
    ngx_http_postpone_filter(ngx_http_request_t *r, ngx_chain_t *in)
    {
        ...
        /* 当前请求不能往out chain发送数据，如果产生了数据，新建一个节点，
           将它保存在当前请求的postponed队尾。这样就保证了数据按序发到客户端 */
        if (r != c->data) {   

            if (in) {
                ngx_http_postpone_filter_add(r, in);
                return NGX_OK;
            }
            ...
            return NGX_OK;
        }
        /* 到这里，表示当前请求可以往out chain发送数据，如果它的postponed链表中没有子请求，也没有数据，
           则直接发送当前产生的数据in或者继续发送out chain中之前没有发送完成的数据 */
        if (r->postponed == NULL) {  
                                    
            if (in || c->buffered) {
                return ngx_http_next_filter(r->main, in);
            }
            /* 当前请求没有需要发送的数据 */
            return NGX_OK;
        }
        /* 当前请求的postponed链表中之前就存在需要处理的节点，则新建一个节点，保存当前产生的数据in，
           并将它插入到postponed队尾 */
        if (in) {  
            ngx_http_postpone_filter_add(r, in);
        }
        /* 处理postponed链表中的节点 */
        do {   
            pr = r->postponed;
            /* 如果该节点保存的是一个子请求，则将它加到主请求的posted_requests链表中，
               以便下次调用ngx_http_run_posted_requests函数，处理该子节点 */
            if (pr->request) {

                ngx_log_debug2(NGX_LOG_DEBUG_HTTP, c->log, 0,
                               "http postpone filter wake \"%V?%V\"",
                               &pr->request->uri, &pr->request->args);

                r->postponed = pr->next;

                /* 按照后序遍历产生的序列，因为当前请求（节点）有未处理的子请求(节点)，
                   必须先处理完改子请求，才能继续处理后面的子节点。
                   这里将该子请求设置为可以往out chain发送数据的请求。  */
                c->data = pr->request;
                /* 将该子请求加入主请求的posted_requests链表 */
                return ngx_http_post_request(pr->request, NULL);
            }
            /* 如果该节点保存的是数据，可以直接处理该节点，将它发送到out chain */
            if (pr->out == NULL) {
                ngx_log_error(NGX_LOG_ALERT, c->log, 0,
                              "http postpone filter NULL output",
                              &r->uri, &r->args);

            } else {
                ngx_log_debug2(NGX_LOG_DEBUG_HTTP, c->log, 0,
                               "http postpone filter output \"%V?%V\"",
                               &r->uri, &r->args);

                if (ngx_http_next_filter(r->main, pr->out) == NGX_ERROR) {
                    return NGX_ERROR;
                }
            }

            r->postponed = pr->next;

        } while (r->postponed);

        return NGX_OK;
    }

再来看ngx_http_finalzie_request函数：

.. code:: c

    void
    ngx_http_finalize_request(ngx_http_request_t *r, ngx_int_t rc) 
    {
      ...
        /* 如果当前请求是一个子请求，检查它是否有回调handler，有的话执行之 */
        if (r != r->main && r->post_subrequest) {
            rc = r->post_subrequest->handler(r, r->post_subrequest->data, rc);
        }

      ...
        
        /* 子请求 */
        if (r != r->main) {  
            /* 该子请求还有未处理完的数据或者子请求 */
            if (r->buffered || r->postponed) {
                /* 添加一个该子请求的写事件，并设置合适的write event hander，
                   以便下次写事件来的时候继续处理，这里实际上下次执行时会调用ngx_http_output_filter函数，
                   最终还是会进入ngx_http_postpone_filter进行处理 */
                if (ngx_http_set_write_handler(r) != NGX_OK) {
                    ngx_http_terminate_request(r, 0);
                }

                return;
            }
            ...
                  
            pr = r->parent;
            

            /* 该子请求已经处理完毕，如果它拥有发送数据的权利，则将权利移交给父请求， */
            if (r == c->data) { 

                r->main->count--;

                if (!r->logged) {

                    clcf = ngx_http_get_module_loc_conf(r, ngx_http_core_module);

                    if (clcf->log_subrequest) {
                        ngx_http_log_request(r);
                    }

                    r->logged = 1;

                } else {
                    ngx_log_error(NGX_LOG_ALERT, c->log, 0,
                                  "subrequest: \"%V?%V\" logged again",
                                  &r->uri, &r->args);
                }

                r->done = 1;
                /* 如果该子请求不是提前完成，则从父请求的postponed链表中删除 */
                if (pr->postponed && pr->postponed->request == r) {
                    pr->postponed = pr->postponed->next;
                }
                /* 将发送权利移交给父请求，父请求下次执行的时候会发送它的postponed链表中可以
                   发送的数据节点，或者将发送权利移交给它的下一个子请求 */
                c->data = pr;   

            } else {
                /* 到这里其实表明该子请求提前执行完成，而且它没有产生任何数据，则它下次再次获得
                   执行机会时，将会执行ngx_http_request_finalzier函数，它实际上是执行
                   ngx_http_finalzie_request（r,0），也就是什么都不干，直到轮到它发送数据时，
                   ngx_http_finalzie_request函数会将它从父请求的postponed链表中删除 */
                r->write_event_handler = ngx_http_request_finalizer;

                if (r->waited) {
                    r->done = 1;
                }
            }
            /* 将父请求加入posted_request队尾，获得一次运行机会 */
            if (ngx_http_post_request(pr, NULL) != NGX_OK) {
                r->main->count++;
                ngx_http_terminate_request(r, 0);
                return;
            }

            return;
        }
        /* 这里是处理主请求结束的逻辑，如果主请求有未发送的数据或者未处理的子请求，
           则给主请求添加写事件，并设置合适的write event hander，
           以便下次写事件来的时候继续处理 */
        if (r->buffered || c->buffered || r->postponed || r->blocked) {

            if (ngx_http_set_write_handler(r) != NGX_OK) {
                ngx_http_terminate_request(r, 0);
            }

            return;
        }

     ...
    } 

