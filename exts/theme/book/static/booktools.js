jQuery.cookie = function(name, value, options) { 
    if (typeof value != 'undefined') { // name and value given, set cookie 
        options = options || {}; 
        if (value === null) { 
            value = ''; 
            options.expires = -1; 
        } 
        var expires = ''; 
        if (options.expires && (typeof options.expires == 'number' || options.expires.toUTCString)) { 
            var date; 
            if (typeof options.expires == 'number') { 
                date = new Date(); 
                date.setTime(date.getTime() + (options.expires * 24 * 60 * 60 * 1000)); 
            } else { 
                date = options.expires; 
            } 
            expires = '; expires=' + date.toUTCString(); // use expires attribute, max-age is not supported by IE 
        } 
        var path = options.path ? '; path=' + options.path : ''; 
        var domain = options.domain ? '; domain=' + options.domain : ''; 
        var secure = options.secure ? '; secure' : ''; 
        document.cookie = [name, '=', encodeURIComponent(value), expires, path, domain, secure].join(''); 
    } else { // only name given, get cookie 
        var cookieValue = null; 
        if (document.cookie && document.cookie != '') { 
            var cookies = document.cookie.split(';'); 
            for (var i = 0; i < cookies.length; i++) { 
                var cookie = jQuery.trim(cookies[i]); 
                // Does this cookie string begin with the name we want? 
                if (cookie.substring(0, name.length + 1) == (name + '=')) { 
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break; 
                } 
            } 
        } 
        return cookieValue; 
    } 
};

hide_sidebar = function(){
    $("div.bodywrapper").css("margin-left", "0px");
    $("div.sphinxsidebar").hide();
    $.cookie("hide_sidebar","1"); 
};

show_sidebar = function(){
    $("div.bodywrapper").css("margin-left", "240px");
    $("div.sphinxsidebar").show();     
    $.cookie("hide_sidebar", "", {expires:-1});    
}

$(function(){
    $('<li class="right"><a href="#" id="toggle_sidebar">切换侧栏(ALT+X)</a> | </li>')
        .insertBefore($(".related:first li:eq(3)"));
        
     $("a#toggle_sidebar").toggle(hide_sidebar, show_sidebar);
     
    $(window).keydown(function(event){
        if(event.altKey && event.keyCode == 88) $("a#toggle_sidebar").click();
    });
     
});