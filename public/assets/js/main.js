'use strict';

console.log('Hey there! Have something to suggest? Visit the Headquarters!');
console.log('TEST');
var lenv = {
    domain: document.domain,
    xhr: '/api/02',
    urlparts: window.location.pathname.split('/'),
    content_types: JSON.parse('{{ CONTENT_TYPES_JSON }}' || null),
    default_avatar: '{{ DEFAULT_AVATAR }}'
};

// Information about the current account

lenv.account = {
    logged: Number("{{ 1 if loggedin else 0 }}"),
    current: "{{ current.record.name|e if loggedin else '' }}",
    id: '{{ current.record.id|e if loggedin else "" }}',
    notifications: JSON.parse("{{ notifications_json or {} }}")
};

console.log('You are', lenv.account.logged ? '' : 'not', 'logged');

// Users can send post and messages from any page of the site, so we 
// got to initialize the attachment vault globally.

lenv.PostAttachments = [];
lenv.MessageAttachments = [];


/*
    WebSocket communication, notifications etc.
*/

lenv.streaming = new WebSocket('ws://' + lenv.domain + ':3671');

lenv.streaming.onmessage = function (event) {
    var sent = JSON.parse(event.data);
    if (sent.action == 'feed') {
        $('.feed').prepend(sent.markup);
    } else if (sent.action == 'notification') {
        // FIXME: clever code to display it
    }
}

///////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////  CRUD //////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////

// POSTS //////////////////////////////////////////////////////////////////////////////////

lenv.posts = {
    create: function(data, cb) {
        var fd = new FormData, params;

        // Add the attachments and content to the FormData instance
        if (data.attachments) {
            for (var i = data.attachments.length - 1; i >= 0; i--) {
                if (data.attachments[i]) // Can be null
                    fd.append('attachment', data.attachments[i].file);
            }
        }

        if (data.content)
            fd.append('content', data.content);

        // Id and type of the base item
        if (data.image)
            fd.append('image', data.image);
        else if (data.post)
            fd.append('post', data.post);
        else;

        // POST request
        console.log('lenv.posts.create', data)
        $.ajax({
            type: 'POST',
            url: lenv.xhr + '/posts',
            data: fd,
            processData: false,
            contentType: false,
            success: function(data) { cb(data) }
        });
    },
    load: function(data, cb) {
        $.ajax({
            url: lenv.xhr + '/posts?' + $.param(data),
            success: function (data) { cb(data) }
        });
    },
    delete: function(ids, cb) {
        $.ajax({
            url: lenv.xhr + '/posts?ids=' + JSON.stringify(ids),
            type: 'DELETE',
            success: function (data) { cb(data) }
        })
    }
};

// IMAGES //////////////////////////////////////////////////////////////////////////////////////////

lenv.images = {
    load: function(data, cb) {
        $.ajax({
            url: lenv.xhr + '/images?' + $.param(data),
            success: function (data) {
                cb(data);
            }
        });
    },
    upload: function (data, cb) {
        var fd = new FormData;

        // Add images to the FormData instance

        for (var i = 0; i < (data.files || []).length; i++) 
            fd.append('image', data.files[i]);

        var params = $.param({
            url: data.url || null,
            id: data.id || null,
            set: data.set || null
        });
        $.ajax({
            url: lenv.xhr + '/images?' + params,
            type: 'POST',
            data: fd,
            processData: false,
            contentType: false,
            success: function(data) { cb(data) }
        });
    },
    delete: function (ids, cb) {
        $.ajax({
            url: lenv.xhr + '/images?ids=' + JSON.stringify(ids),
            type: 'DELETE',
            success: function (data) { cb(data) }
        });
    }
};


// ACCS /////////////////////////////////////////////////////////////////////////////

lenv.account_data = {
    get: function (data, cb) {
        $.ajax({
            url: lenv.xhr + '/records?' + $.param(data),
            success: function (data) { cb(data) }
        })
    },
    update: function (data, cb) {
        $.ajax({
            type: 'PUT',
            url: lenv.xhr + '/records/set', // Empty values will be eliminated anyway
            data: JSON.stringify(data),
            success: function (data) { cb(data) }
        })
    },
    unset: function (data, cb) {
        $.ajax({
            url: lenv.xhr + '/records/unset',
            type: 'PUT',
            data: data,
            success: function(data) {
                console.log(data);
            }
        });
    }
};


// NOTIFICATIONS ////////////////////////////////////////////////////////////////////////


lenv.notifications  = {
    get: function(data, cb) {
        $.ajax({
            url: lenv.xhr + '/notifications',
            success: function(data) {
                console.log(data)
            }
        })
    },
    delete: function(ids) {
        if (typeof ids != 'undefined') {
            $.ajax({
                url: lenv.xhr + '/notifications',
                type: 'DELETE',
                data: JSON.stringify({'ids': ids}),
                success: function(data) {
                    console.log(data)
                }
            });
        } else {
            $.ajax({
                url: lenv.xhr + '/notifications',
                type: 'DELETE',
                success: function(data) {
                    console.log(data)
                }
            });
        }
    }
}


/*///////////////////////////////////////////////////////////////////////////////////
    FILE OPERATIONS
///////////////////////////////////////////////////////////////////////////////////*/


/*
    Determine the image type by starting bytes. 
    See the configuration file for the list of supported
    image types.
    `contents` is the result of readAsBinaryString method of FileReader.
*/
function image_type(contents) {

    var bytes = '';
    for (var i = 0; i < 4; i++)
        bytes += contents[i].charCodeAt(0).toString(16).toLowerCase();

    if (bytes == '47494638') {
        return ['image', 'gif'];
    } else if (bytes == '89504e47') {
        return ['image', 'png'];
    } else {
        var nextbytes = '';
        // From 6th to 10th byte
        for (var i = 6; i < 10; i++) 
            nextbytes += contents[i].charCodeAt(0).toString(16).toLowerCase();
        if (!bytes.indexOf('ffd8ff') && (nextbytes == '4a464946' || nextbytes == '45786966'))
            return ['image', 'jpeg'];
        return false;   
    }
}

/*
    Add all files from `input.files` to `storage` and display them
    in `box`
*/
function attach(input, box, storage) {

    // Check if file is a valid attachment (used only inside `attach`)

    function _valid(file) {
        var res = file.slice(0, 10),
            reader = new FileReader;
        reader.onload = function(ev) {
            var type = image_type(ev.target.result) || false;
            console.log('Name:', file.name, 'detected type:', type, 'size:', file.size);
            // 10 Megabytes 
            // FIXME: Add the value from config
            if (type && file.size <= 10 * 1024 * 1024) {
                // For data URL
                reader = new FileReader();
                // Read the full file
                reader.onload = function(e) { 
                    // Construct data URI for displaying
                    var uri = 'data:' + type[0] + '/' + type[1] + ';';
                    uri += 'base64,' + btoa(e.target.result);
                    storage.push({file: file, url: uri, type: type});

                    var at = $('<li>'),
                        arrow = $('<div>', {'class': 'arrow'})

                    $('<div>', {'class': 'fill', 
                                style: 'background-image: url(' + uri + ');' + 'height: 60px'
                                }).appendTo(at);
                    
                    arrow.append($('<div>', {'class': 'delete', 'attachment-id': storage.length}));
                    arrow.appendTo(at)
                    box.append(at);

                    // Allows to select the same file
                    input.value = null;
                }
                reader.readAsBinaryString(file);
            }
        }
        reader.readAsBinaryString(res);
    }
    for (var i = 0; i < input.files.length; i++)
        _valid(input.files[i]);
}


/*/////////////////////////////////////////////////////////////////////////////////
    COMMON UI OPS
/////////////////////////////////////////////////////////////////////////////////*/

/*
    Scroll to the top of the page
*/
$.fn.stt = function(speed) {
    var $this = $(this);
    $this.hide();
    if ( $(window).scrollTop() !=0 ) {
        $this.show();
    }
    $(window).scroll(function() {
        if($(window).scrollTop() == 0){
            $this.stop(true,true).fadeOut(150);
        } else {
            $this.fadeIn(150);
        }
    });
    $($this).click(function(e){
        e.preventDefault();
        $("html,body").animate({ scrollTop: 0 }, speed);
    });
}


/*
    Submit on Ctrl + Enter
*/
$.fn.ctrlEnter = function (btns, fn) {
    // IIFE fits here perfectly, as without it we get problems when
    // there're more than 1 form on the page.
    (function(thiz, buttons){

        function performAction (e) {
            fn.call(thiz, e);
            return false;
        }

        buttons.bind("click", performAction);

        thiz.keydown(function (e) {
            if (e.keyCode === 13 && e.ctrlKey) {
                performAction(e);
                e.preventDefault();
            }
        });

    })($(this), $(btns));

}

/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////  OVERLAYS  //////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/* POSTS */////////////////////////////////////////////////////////////////////////////////////////////////////////

$('#post-overlay-reply .no-reply').click(function() {
    $('#post-overlay-reply').hide();
    $('.post-container', '#post-overlay-reply').remove();
});

$('#show-gnpo').click(function() {
    $('#gnpo').show(50);
    $('#post-overlay-reply .no-reply').trigger('click');
    $('#post-overlay-textarea').focus();
});

$('#gnpo .attachments-input').click(function() {
    $('#post-overlay-attach').trigger('click');
});

document.getElementById('post-overlay-attach').addEventListener('change', function() {
    attach(this, $('#post-overlay-attachments'), lenv.PostAttachments);
});

$(document).on('click', '#post-overlay-attachments .delete', function(e) {
    var id = +$(this).attr('attachment-id');
    $(this).parents().eq(1).remove()
    lenv.PostAttachments[id - 1] = null;
});

$('#post-overlay-textarea').ctrlEnter('#post-overlay-submit', function() {
    var target = $('.post-container', '#post-overlay-reply');
    lenv.posts.create({
        content: $(this).val(), 
        attachments: lenv.PostAttachments,
        post: target.attr('post-id') || null
    }, function(data) {
        $(".hint", '#gnpo .action-bar').html(data.text);
        console.log(data)
        if (data.success) {
            $('#post-overlay-reply .no-reply').trigger('click');
            lenv.PostAttachments.length = 0;
            $(this).val('');
            $('#gnpo').hide();
            $('#post-overlay-attachments').empty();
        }
    });
});

/* IMAGES *////////////////////////////////////////////////////////////////////////////////////////////////////

$('.images-upload-dialog').click(function() {
    $('#giuo').show();
});

$('#images-upload-select').click(function() {
    $('#images-upload-input').click();
});


$('#upload-images-url').change(function() {
    lenv.images.upload({url: $(this).val()}, function(data) {
        $('#giuo .hint').html(data.text);
    });
});

document.getElementById('images-upload-input').addEventListener("change", function () {
    lenv.images.upload({files: this.files}, function(data){
        console.log(data.text)
        $('#giuo .hint').html(data.text);
    });
}, false);


/* NOTIFICATIONS *////////////////////////////////////////////////////////////////////////////////////////

$('#show-noto').click(function() {
    $('#noto').show(50);
});

$('.mark-read', '#noto').click(function() {
    var not_container = $(this).parent();
    lenv.notifications.delete([not_container.data('id')])
    not_container.remove();
});

$('.mark-all-read', '#noto').click(function() {
    lenv.notifications.delete()
    $('.overlay-shadow').trigger('click');
});

/* SITE-WIDE EVENT BINDINGS *////////////////////////////////////////////////////////////////////////////

// Esc must close the overlay in any case
$(document).keydown(function(e) {
    if (e.keyCode == 27) 
        $('.overlay-shadow').trigger('click');
});

$('.overlay-shadow').click(function() {
    $('.overlay').hide();
});
    
$('.displayable').click(function() {
    var item = $(this);
    var type = Number($(this).attr('type')),
        id = $(this).attr('item-id');
    $('.showcase').show();
    if (type == lenv.content_types.image) {
        lenv.images.load({id: id, showcase: 1}, function(data) {
            if (data.success) {
                $('.showcase').remove();
                var new_sc = $(data.showcase);
                // new id
                new_sc.attr('id', 'showcase');
                new_sc.insertAfter(item);
                location.href = "#showcase";
            }
        });
    }

});

$(document).on('click', '.vote-button', function () {
    var button = $(this),
        action = button.attr('action'),
        params;

    if (button.attr('post-id')) params = {'post': button.attr('post-id')}
    else params = {'image': button.attr('image-id')} 

    $.ajax({
        url: lenv.xhr + '/ratings/' + action + '?' + $.param(params),
        type: 'PUT',
        success: function (data) {
            console.log(data);
            button.attr('action', (action != 'unvote') ? 'unvote' : button.attr('bound'));
        }
    })
});

$(document).on('click', '.fix-post-button', function () {
    var post_id = $(this).attr('post-id');
    console.log(post_id);
    lenv.records.update({'fixed_post': post_id}, function () {});
});

$(document).on('click', '.unfix-post-button', function () {
    lenv.records.unset(['fixed_post'], function () {});
});

$(document).on('click', '.delete-post-button', function () {
    var post_id = $(this).attr('post-id');
    lenv.posts.delete([post_id], function(html) {
         console.log(html);
    });
});

$(document).on('click', '.share-post-button', function () {
    var post_id = $(this).attr('post-id');
    lenv.posts.create({'post': post_id});
});

$(document).on('click', '.reply-to-post-button', function () {
    var post = $('#post-' + $(this).attr('post-id')),
        cloned = post.clone(true, true); // Do not copy events?
    $('#post-overlay-reply .no-reply').trigger('click');
    cloned.addClass('small-post');
    cloned.appendTo('#gnpo .reply');
    $('#gnpo .reply').show();   
    $('#gnpo').show();
});

$(document).ready(function () {

    // Header buttons and actions

    $(".action-header-toggle").click(function() {

        $(".action-header").slideToggle(150, function(){
            $('.action-header-toggle').toggleClass('expanded');
        });

        $('.header-action-field').focus();
    });

    $("li.link-to-top", 'nav.left-nav > ul').stt(25);
});











/////////////////////////////////////////////////////////////
// AUTH BASE
/////////////////////////////////////////////////////////////

var pwd_field = $('#pwd'),
    toggle_pwd = $('#toggle-pwd'); 
toggle_pwd.click(function () {
    if (pwd_field.attr('type') === 'password') {
        pwd_field.attr('type', 'text');
        toggle_pwd.text("Hide Password");
    } else {
        pwd_field.attr('type', 'password');
        toggle_pwd.text("Show Password");
    }
});




////////////////////////////////////////////////////////////////////////////////////////
// SIGNUP 
////////////////////////////////////////////////////////////////////////////////////////

$("#auth-name").change(function(){
    lenv.account_data.get(
        {'name': $(this).val()},
        function(data) {
            if (data.record) {
                var e = $('<div>', {
                        'id': 'name-check',
                        'class': 'message error',
                        'text': 'This name is already taken'
                    });
                $('#auth-messages').append(e);
            } else $('#name-check').remove();
    });
    
});

////////////////////////////////////////////////////////////////////////
// PROFILE
////////////////////////////////////////////////////////////////////////////////

'use strict';
/* Public information */
lenv.Profile = {'Name': "{{ page_profile.name|e }}",
                'Picture': "{{ page_profile.avatar.raw or '' }}"};

$(document).ready(function() {

    // View larger profile picture by clicking on zoom button

    $('.pic-zoom').click(function() {
        
        // Only if profile picture is defined

        if (lenv.Profile.Picture) {
            $('#full-screen-container').show(50);
            $('#profile-avatar').trigger('click');
        }
    });



    $('.pictures-container div:not(:last-child)').click(function () {

        $('#full-screen-container').show(50);

        image_id = $(this).attr('image-inner-id');
        $.ajax({
            url: lenv.xhr + '/images/load?id='+image_id,
            success: function(data) {
                console.log(data)
                $('#fs-image-container').FullScreenImage(data.output.image.dimensions, data.output.image.url.large, function(){
                    console.log('Large picture displayed');
                });
            }
        });

    });
    /*   If user is logged in and viewing his own profile page he can
     change a cover photo directly from profile page */

    $('.cover-picture-container').hover(function(){
        $('.cover-photo-action-bar').fadeIn(150);
    }, function(){
        $('.cover-photo-action-bar').fadeOut(150);
    });

    // Profile picture overlay
    $(".profile-pic").hover(function() {
        $(this).find("div.profile-pic-overlay").stop(false,true).fadeIn(150);
    },
    function() {
        $(this).find("div.profile-pic-overlay").stop(false,true).fadeOut(150);
    });


    // If user is logged in and viewing his own profile page he can 
    // post instantly

    


    $('.unpin-cover-photo').click(function(){
     $.ajax({
         url: lenv.xhr + '/images/hide_cover',
         success: function(){
             $('.cover-picture').empty();
         }
     });
    });

    $('#change-cover-photo').click(function(){
        $('#change-cover-photo-box').show(50);
        lenv.images.load({number: 15, type: 'thumb'}, function(data) {
            console.log(data);
            $('.change-buttons-content').html(data.output.html);

            // Class of an element loaded by the ajax request
            $('.change-buttons-content div').click(function () {
                id = $(this).attr('image-inner-id');
                $.ajax({
                    url: lenv.xhr+'/images/upload?set=cover&id=' + id,
                    success: function(data) {
                        console.log(data);
                        if (data.success) {
                            $('#change-cover-photo-box').hide();
                            $('#profile-cover-photo').attr('src', data.output.link);
                        }
                    }
                });
            });
        });
    });

    //
    // Load more posts
    // 

    var loading = false;
    
    $(window).scroll(function() {
        var h = $('.posts').height(),
            st = $(window).scrollTop(),
            start_id = $(".page-post:last").attr("post-id");
        if(st >= 0.7 * h && !loading && h > 500){
            loading = true;
            lenv.posts.load({start: start_id, page: lenv.Profile.Name}, function(data) {
                $(".posts").append(data.output.html);
                loading = false;
            });
        }
    });

    /*  
        RELATIONS BETWEEN USERS
    */

    $(document).on("click", '.follow-button', function(e) {
        var thiz = $(this),
            name = thiz.attr('name');
        $.ajax({
            url: lenv.xhr+'/relations/follow?name=' + name,
            success: function(data) {
                console.log(data);
                if (data.success) {
                    thiz.removeClass('follow-button')
                    thiz.addClass('unfollow-button');
                    thiz.html('Unfollow');
                    return false;
                    // voila! Button is totally different now
                }
            }
        });
    });

    $(document).on("click", '.unfollow-button', function(e) {
        var thiz = $(this),
            name = thiz.attr('name');
        $.ajax({
            url: lenv.xhr + '/relations/unfollow?name=' + name,
            success: function(data) {
                console.log(data);
                if (data.success) {
                    thiz.removeClass('unfollow-button')
                    thiz.addClass('follow-button');
                    thiz.html('Follow');
                    return false;
                }
            }
        });
        
    });

    $(document).on("click", '.add-friend-button', function (e) {
        var thiz = $(this),
            name = thiz.attr('name');
        $.ajax({
            url: lenv.xhr + '/relations/friend?name=' +  name,
            success: function(data) {
                console.log(data);
                if (data.success) {
                    thiz.removeClass('add-friend-button');
                    if (data.output.request) {
                        thiz.addClass('cancel-request-button');
                        thiz.html('Cancel request');
                    } else if (data.output.friends) {
                        thiz.addClass('unfriend');
                        thiz.html('Remove from friends');
                    }
                    return false;
                }
            }
        });
    });

    $(document).on("click", '.cancel-request-button', function (e) {
        var thiz = $(this),
            name = thiz.attr('name');
        $.ajax({
            url: lenv.xhr+'/relations/cancel?name=' +  name,
            success: function(data) {
                console.log(data);
                if (data.success) {
                    thiz.removeClass('cancel-request-button');
                    thiz.addClass('add-friend-button');
                    thiz.html('Add to friends');
                    return false;
                }
            }
        });
    });

    $(document).on("click", '.confirm-friends-button', function (e) {
        var thiz = $(this),
            name = thiz.attr('name');
        $.ajax({
            url: lenv.xhr+'/relations/confirm?name='+ name,
            success: function(data) {
                console.log(data);
                if (data.success) {
                    thiz.attr('class', 'unfriend');
                    thiz.html('Remove from friends');
                    return false;
                }
            }
        });
    });

    $(document).on('click', '.unfriend', function (e) {
        var thiz = $(this),
            name = thiz.attr('name');
        $.ajax({
            url: lenv.xhr+'/relations/unfriend?name='+ name,
            success: function(data) {
                console.log(data);
                if (data.success) {
                    thiz.removeClass('unfriend');
                    thiz.addClass('add-friend-button');
                    thiz.html('Add to friends');
                    return false;
                }
            }
        });
    });

});

////////////////////////////////////////////////////////////////////
// IMAGES
////////////////////////////////////////////////////////////////////


 $(document).ready( function() {
    var images_input = document.getElementById("images-upload"), 
        del_selecting = false,
        def_text = $('.inner-delete-button').html(),
        deletion = new Array,
        container = $('.images-page-container');

    function _error_text(number) {
       word = (number == 1) ? 'was' : 'were';
       text = 'There ' + word + ' ' + number + ' error';
       if (number != 1) 
           text += 's';
       return text;
    }

    function resize_images () {     
        container_w = container.width();
        img_margin = 2;
        max_imgs = Math.ceil(container_w/(2*img_margin+100));
        each_w = container_w/max_imgs-2*img_margin; 
        console.log(container_w, max_imgs, each_w);
        images = container.find('img');
        images.css('width', each_w);
        images.css('height', each_w);
    }

    resize_images();

    $(window).resize(function(){
        resize_images();
    });

    // $('.inner-delete-button').click(function(event) {
    //     del_selecting = ( del_selecting ) ? false : true;
    //     console.log(del_selecting);
    //     if ( del_selecting ) {
    //         $(this).html('Unselect');
    //         $('.confirm-deletion-button').show();
    //     } else {
    //         $(this).html(def_text);
    //         $('.confirm-deletion-button').hide();
    //         del_selecting = false;
    //         deletion.length = 0;
    //         console.log(deletion);
    //         $('.images-page-container div').removeClass('bleached');
    //     }

    //     $('.images-page-container div').click(function () {
    //         if ( del_selecting ) {
    //             id = $(this).attr('image-inner-id');
    //             console.log(id);

    //             $(this).toggleClass('bleached')

    //             if ( !$(this).hasClass('bleached') ) {
    //                 index = deletion.indexOf(id);
    //                 deletion.splice(index, 1);
    //                 console.log(deletion);  
    //             } else {
    //                 deletion.push(Number(id));
    //                 console.log(deletion);  
    //             }


    //         }

    //     });
    // });

    // $('.confirm-deletion-button').click(function () {

    //     if ( deletion.length > 0) {
    //         $.ajax({
    //             url: lenv.AjaxRequests+'/images/delete',
    //             method: 'POST',
    //             data: { ids: JSON.stringify(deletion) },
    //             dataType: 'json',
    //             success: function (data) {
    //                 console.log(data);
    //                 for (var i = deletion.length - 1; i >= 0; i--) {
    //                     console.log(deletion[i]);
    //                     selector = 'div#uploaded-image-'+deletion[i]
    //                     $(selector).remove();
    //                     if ( $('.images-page-container').html().trim().length == 0 ) {
    //                         console.log('Last');
    //                         $('.images-page-container').html("<div class='block'>No images</div>");
    //                     } else {

    //                     }
    //                 }
    //             }
    //     });
    //     }   
    // });


 // Plain XHR upload

});



////////////////////////////////////////////////////////
///////////////////////////////
// ACCOUNTS
//////////////////////////////
////////////////////////////////////////////////////////

(document).ready( function(){
    var cover_input = document.getElementById("cover-input"),
        profile_input = document.getElementById("avatar-input"); 

    // Change real name

    $("#profile-settings-real-name-field").change(function(){
        lenv.account_data.update({
           'real_name': $(this).val()
        }, function(data) {
            $("#real-name-hint").html(data.response);    
        });
    });

    // Save country

    $("#country-settings-dropdown").change(function() {
        lenv.account_data.update({
           'country': $(this).val()
        }, function(data) {
            $("#country-hint").html(data.response);    
        });
    });

    // Change username

    $("#change-username-field").change(function() {
        lenv.account_data.update({
           'name': $(this).val()
        }, function(data) {
            console.log(data);
            $("#change-username-hint").html(data.response);    
        });
        
    });

    // Save website

    $("#profile-settings-change-website").change(function() {
        lenv.account_data.update({
           'website': $(this).val()
        }, function(data) {
            console.log(data);
            $("#save-website-hint").html(data.response);    
        });
    });

    
    cover_input.addEventListener("change", function() {

        if (this.files.length != 1) {
            $('#cover-photo-upload-hint').html('Select exatly one file');
            return;
        }
        lenv.images.upload({files: this.files, set: 'cover'}, function(data){
            if ( data.success == 1 ) {
                $('#cover-photo-upload-hint').html(data.response);
            } else {
                $('#cover-photo-upload-hint').html('Something went wrong');
            }

            $(cover_input).val('');
        });

    }, false);

    profile_input.addEventListener("change", function() {
        if (this.files.length != 1) {
            $('#profile-photo-upload-hint').html('Select exactly one image');
            return;
        }
        lenv.images.upload({files: this.files, set: 'avatar'}, function(data) {
            if ( data.success == 1 ) {
                $('#profile-photo-upload-hint').html(data.response);
            } else {
                $('#profile-photo-upload-hint').html('Something went wrong');
            }
            $( profile_input ).val('');
        });
    }, false);

});




////////

/// SECURITY
/////////////


$(document).ready(function(){
    $('#change-pass-button').click(function (){
        old_pwd = $('#old-password').val();
        new_pwd = $('#new-password').val();
        $.ajax({
            url: lenv.AjaxRequests + '/security-settings/password',
            data: { 'old-pwd': old_pwd, 'new-pwd': new_pwd },
            type: 'post',
            success: function(data) {
                $("#password-change-hint").html(data.response);
            }   
            
        });
    });

    $('#update-email').change(function (){
        email_val = $(this).val();
        $.ajax({
            url: lenv.AjaxRequests + '/security-settings/email',
            data: { email: email_val },
            type: 'post',
            success: function(data) {
                $("#email-update-hint").html(data.response);
            }   
            
        });
    });
});


/////////////////////////////////////////////////////////
// SIGN IN
////////////////////////////////////////////////////////

$(document).ready(function() {
    $(".cb-enable").click(function() {
        var a = $(this).parents(".remember-switch");
        $(".cb-disable", a).removeClass("selected");
        $(this).addClass("selected");
        $("#cb-remember", a).attr("checked", !0)
    });
    $(".cb-disable").click(function() {
        var a = $(this).parents(".remember-switch");
        $(".cb-enable", a).removeClass("selected");
        $(this).addClass("selected");
        $("#cb-remember", a).attr("checked", !1)
    });
    $("#cb-remember").attr("checked") ? ($(".cb-disable").removeClass("selected"), $(".cb-enable").addClass("selected")) :
        ($(".cb-disable").addClass("selected"), $(".cb-enable").removeClass("selected"))
});



/////////////////////////////////////////////
/// ACCOUNTS LAYOUT
///////////////////////////////////////////////
// FIXME
$(document).ready(function(){var a=location.href.toLowerCase();$(".account-nav li a").each(function(){-1<a.indexOf(this.href.toLowerCase())&&($("li.current").removeClass("current"),$(this).parent().addClass("current"))})});