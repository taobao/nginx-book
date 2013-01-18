模块开发
============

upstream模块
------------

nginx模块一般被分成三大类：handler、filter和upstream。前面的章节中，读者已经了解了handler、filter。利用这两类模块，可以使nginx轻松完成任何单机工作。而本章介绍的upstream，将使nginx将跨越单机的限制，完成网络数据的接收、处理和转发。

数据转发功能，为nginx提供了跨越单机的横向处理能力，使nginx摆脱只能为终端节点提供单一功能的限制，而使它具备了网路应用级别的拆分、封装和整合的战略功能。在云模型大行其道的今天，数据转发使nginx有能力构建一个网络应用的关键组件。当然，一个网络应用的关键组件往往一开始都会考虑通过高级开发语言编写，因为开发比较方便，但系统到达一定规模，需要更重视性能的时候，这些高级语言为了达成目标所做的结构化修改所付出的代价会使nginx的upstream模块就呈现出极大的吸引力，因为他天生就快。作为附带，nginx的配置提供的层次化和松耦合使得系统的扩展性也可能达到比较高的程度。

言归正传，下面介绍upstream的写法。

upstream模块接口
+++++++++++++++++++

从本质上说，upstream属于handler，只是他不产生自己的内容，而是通过请求后端服务器得到内容，所以才称为upstream（上游）。请求并取得响应内容的整个过程已经被封装到nginx内部，所以upstream模块只需要开发若干回调函数，完成构造请求和解析响应等具体的工作。

这些回调函数如下表所示：

+-------------------+--------------------------------------------------------------+
|create_request     |生成发送到后端服务器的请求缓冲（缓冲链）。                    |
+-------------------+--------------------------------------------------------------+
|reinit_request     |在某台后端服务器出错的情况，nginx会尝试另一台后端服务器。     |
|                   |nginx选定新的服务器以后，会先调用此函数，然后再次调用         |
|                   |create_request，以重新初始化upstream模块的工作状态。          |
+-------------------+--------------------------------------------------------------+
|process_header     |处理后端服务器返回的信息头部。所谓头部是与upstream server     |
|                   |通信的协议规定的，比如HTTP协议的header部分，或者memcached     |
|                   |协议的响应状态部分。                                          |
+-------------------+--------------------------------------------------------------+
|abort_request      |在客户端放弃请求时被调用。不需要在函数中实现关闭后端服务      |
|                   |器连接的功能，系统会自动完成关闭连接的步骤，所以一般此函      |
|                   |数不会进行任何具体工作。                                      |
+-------------------+--------------------------------------------------------------+
|finalize_request   |正常完成与后端服务器的请求后调用该函数，与abort_request       |
|                   |相同，一般也不会进行任何具体工作。                            |
+-------------------+--------------------------------------------------------------+
|input_filter       |处理后端服务器返回的响应正文。nginx默认的input_filter会       |
|                   |将收到的内容封装成为缓冲区链ngx_chain。该链由upstream的       |
|                   |out_bufs指针域定位，所以开发人员可以在模块以外通过该指针      |
|                   |得到后端服务器返回的正文数据。memcached模块实现了自己的       |
|                   |input_filter，在后面会具体分析这个模块。                      |
+-------------------+--------------------------------------------------------------+
|input_filter_init  |初始化input filter的上下文。nginx默认的input_filter_init      |
|                   |直接返回。                                                    |
+-------------------+--------------------------------------------------------------+

memcached模块分析
++++++++++++++++++++++++++++++

memcache是一款高性能的分布式cache系统，得到了非常广泛的应用。memcache定义了一套私有通信协议，使得不能通过HTTP请求来访问memcache。但协议本身简单高效，而且memcache使用广泛，所以大部分现代开发语言和平台都提供了memcache支持，方便开发者使用memcache。

nginx提供了ngx_http_memcached模块，提供从memcache读取数据的功能，而不提供向memcache写数据的功能。作为web服务器，这种设计是可以接受的。

下面，我们开始分析ngx_http_memcached模块，一窥upstream的奥秘。

Handler模块？
^^^^^^^^^^^^^^^

初看memcached模块，大家可能觉得并无特别之处。如果稍微细看，甚至觉得有点像handler模块，当大家看到这段代码以后，必定疑惑为什么会跟handler模块一模一样。

.. code-block:: none

        clcf = ngx_http_conf_get_module_loc_conf(cf, ngx_http_core_module);
        clcf->handler = ngx_http_memcached_handler;

因为upstream模块使用的就是handler模块的接入方式。同时，upstream模块的指令系统的设计也是遵循handler模块的基本规则：配置该模块才会执行该模块。

.. code-block:: none

        { ngx_string("memcached_pass"),
          NGX_HTTP_LOC_CONF|NGX_HTTP_LIF_CONF|NGX_CONF_TAKE1,
          ngx_http_memcached_pass,
          NGX_HTTP_LOC_CONF_OFFSET,
          0,
          NULL }

所以大家觉得眼熟是好事，说明大家对Handler的写法已经很熟悉了。

Upstream模块！
^^^^^^^^^^^^^^^

那么，upstream模块的特别之处究竟在哪里呢？答案是就在模块处理函数的实现中。upstream模块的处理函数进行的操作都包含一个固定的流程。在memcached的例子中，可以观察ngx_http_memcached_handler的代码，可以发现，这个固定的操作流程是：

1\. 创建upstream数据结构。

.. code-block:: none

        if (ngx_http_upstream_create(r) != NGX_OK) {
            return NGX_HTTP_INTERNAL_SERVER_ERROR;
        }

2\. 设置模块的tag和schema。schema现在只会用于日志，tag会用于buf_chain管理。

.. code-block:: none

        u = r->upstream;

        ngx_str_set(&u->schema, "memcached://");
        u->output.tag = (ngx_buf_tag_t) &ngx_http_memcached_module;

3\. 设置upstream的后端服务器列表数据结构。

.. code-block:: none

        mlcf = ngx_http_get_module_loc_conf(r, ngx_http_memcached_module);
        u->conf = &mlcf->upstream;

4\. 设置upstream回调函数。在这里列出的代码稍稍调整了代码顺序。

.. code-block:: none

        u->create_request = ngx_http_memcached_create_request;
        u->reinit_request = ngx_http_memcached_reinit_request;
        u->process_header = ngx_http_memcached_process_header;
        u->abort_request = ngx_http_memcached_abort_request;
        u->finalize_request = ngx_http_memcached_finalize_request;
        u->input_filter_init = ngx_http_memcached_filter_init;
        u->input_filter = ngx_http_memcached_filter;

5\. 创建并设置upstream环境数据结构。

.. code-block:: none 

        ctx = ngx_palloc(r->pool, sizeof(ngx_http_memcached_ctx_t));
        if (ctx == NULL) {
            return NGX_HTTP_INTERNAL_SERVER_ERROR;
        }

        ctx->rest = NGX_HTTP_MEMCACHED_END;
        ctx->request = r;

        ngx_http_set_ctx(r, ctx, ngx_http_memcached_module);

        u->input_filter_ctx = ctx;

6\. 完成upstream初始化并进行收尾工作。

.. code-block:: none

        r->main->count++;
        ngx_http_upstream_init(r);
        return NGX_DONE;

任何upstream模块，简单如memcached，复杂如proxy、fastcgi都是如此。不同的upstream模块在这6步中的最大差别会出现在第2、3、4、5上。其中第2、4两步很容易理解，不同的模块设置的标志和使用的回调函数肯定不同。第5步也不难理解，只有第3步是最为晦涩的，不同的模块在取得后端服务器列表时，策略的差异非常大，有如memcached这样简单明了的，也有如proxy那样逻辑复杂的。这个问题先记下来，等把memcached剖析清楚了，再单独讨论。

第6步是一个常态。将count加1，然后返回NGX_DONE。nginx遇到这种情况，虽然会认为当前请求的处理已经结束，但是不会释放请求使用的内存资源，也不会关闭与客户端的连接。之所以需要这样，是因为nginx建立了upstream请求和客户端请求之间一对一的关系，在后续使用ngx_event_pipe将upstream响应发送回客户端时，还要使用到这些保存着客户端信息的数据结构。这部分会在后面的原理篇做具体介绍，这里不再展开。

将upstream请求和客户端请求进行一对一绑定，这个设计有优势也有缺陷。优势就是简化模块开发，可以将精力集中在模块逻辑上，而缺陷同样明显，一对一的设计很多时候都不能满足复杂逻辑的需要。对于这一点，将会在后面的原理篇来阐述。


回调函数
^^^^^^^^^^^

前面剖析了memcached模块的骨架，现在开始逐个解决每个回调函数。

1\. ngx_http_memcached_create_request：很简单的按照设置的内容生成一个key，接着生成一个“get $key”的请求，放在r->upstream->request_bufs里面。

2\. ngx_http_memcached_reinit_request：无需初始化。

3\. ngx_http_memcached_abort_request：无需额外操作。

4\. ngx_http_memcached_finalize_request：无需额外操作。

5\. ngx_http_memcached_process_header：模块的业务重点函数。memcache协议将头部信息被定义为第一行文本，可以找到这段代码证明：

.. code-block:: none

        for (p = u->buffer.pos; p < u->buffer.last; p++) {
            if ( * p == LF) {
            goto found;
        }

如果在已读入缓冲的数据中没有发现LF('\n')字符，函数返回NGX_AGAIN，表示头部未完全读入，需要继续读取数据。nginx在收到新的数据以后会再次调用该函数。

nginx处理后端服务器的响应头时只会使用一块缓存，所有数据都在这块缓存中，所以解析头部信息时不需要考虑头部信息跨越多块缓存的情况。而如果头部过大，不能保存在这块缓存中，nginx会返回错误信息给客户端，并记录error log，提示缓存不够大。

process_header的重要职责是将后端服务器返回的状态翻译成返回给客户端的状态。例如，在ngx_http_memcached_process_header中，有这样几段代码：

.. code-block:: none

        r->headers_out.content_length_n = ngx_atoof(len, p - len - 1);

        u->headers_in.status_n = 200;
        u->state->status = 200;

        u->headers_in.status_n = 404;
        u->state->status = 404;

u->state用于计算upstream相关的变量。比如u->status->status将被用于计算变量“upstream_status”的值。u->headers_in将被作为返回给客户端的响应返回状态码。而第一行则是设置返回给客户端的响应的长度。

在这个函数中不能忘记的一件事情是处理完头部信息以后需要将读指针pos后移，否则这段数据也将被复制到返回给客户端的响应的正文中，进而导致正文内容不正确。

.. code-block:: none

        u->buffer.pos = p + 1;

process_header函数完成响应头的正确处理，应该返回NGX_OK。如果返回NGX_AGAIN，表示未读取完整数据，需要从后端服务器继续读取数据。返回NGX_DECLINED无意义，其他任何返回值都被认为是出错状态，nginx将结束upstream请求并返回错误信息。

6\. ngx_http_memcached_filter_init：修正从后端服务器收到的内容长度。因为在处理header时没有加上这部分长度。

7\. ngx_http_memcached_filter：memcached模块是少有的带有处理正文的回调函数的模块。因为memcached模块需要过滤正文末尾CRLF "END" CRLF，所以实现了自己的filter回调函数。处理正文的实际意义是将从后端服务器收到的正文有效内容封装成ngx_chain_t，并加在u->out_bufs末尾。nginx并不进行数据拷贝，而是建立ngx_buf_t数据结构指向这些数据内存区，然后由ngx_chain_t组织这些buf。这种实现避免了内存大量搬迁，也是nginx高效的奥秘之一。

本节小结
++++++++++++

在这一节里，大家对upstream模块的基本组成有了一些认识。upstream模块是从handler模块发展而来，指令系统和模块生效方式与handler模块无异。不同之处在于，upstream模块在handler函数中设置众多回调函数。实际工作都是由这些回调函数完成的。每个回调函数都是在upstream的某个固定阶段执行，各司其职，大部分回调函数一般不会真正用到。upstream最重要的回调函数是create_request、process_header和input_filter，他们共同实现了与后端服务器的协议的解析部分。
