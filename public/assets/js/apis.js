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
            url: VARS.xhr + '/posts',
            data: fd,
            processData: false,
            contentType: false,
            success: function(data) { cb(data) }
        });
    },
    load: function(data, cb) {
        $.ajax({
            url: VARS.xhr + '/posts?' + $.param(data),
            success: function (data) { cb(data) }
        });
    },
    delete: function(ids, cb) {
        $.ajax({
            url: VARS.xhr + '/posts?ids=' + JSON.stringify(ids),
            type: 'DELETE',
            success: function (data) { cb(data) }
        })
    }
};

// IMAGES /////////////////////////////////////////////////////////////////////////////////

lenv.images = {
    load: function(data, cb) {
        $.ajax({
            url: VARS.xhr + '/images?' + $.param(data),
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
            url: VARS.xhr + '/images?' + params,
            type: 'POST',
            data: fd,
            processData: false,
            contentType: false,
            success: function(data) { cb(data) }
        });
    },
    delete: function (ids, cb) {
        $.ajax({
            url: VARS.xhr + '/images?ids=' + JSON.stringify(ids),
            type: 'DELETE',
            success: function (data) { cb(data) }
        });
    }
};


// ACCS ///////////////////////////////////////////////////////////////////////////////////

lenv.account_data = {
    get: function (data, cb) {
        $.ajax({
            url: VARS.xhr + '/records?' + $.param(data),
            success: function (data) { cb(data) }
        })
    },
    update: function (data, cb) {
        $.ajax({
            type: 'PUT',
            url: VARS.xhr + '/records/set', // Empty values will be eliminated anyway
            data: JSON.stringify(data),
            success: function (data) { cb(data) }
        })
    },
    unset: function (data, cb) {
        $.ajax({
            url: VARS.xhr + '/records/unset',
            type: 'PUT',
            data: data,
            success: function(data) {
                console.log(data);
            }
        });
    }
};


// NOTIFICATIONS //////////////////////////////////////////////////////////////////////////


lenv.notifications  = {
    get: function(data, cb) {
        $.ajax({
            url: VARS.xhr + '/notifications',
            success: function(data) {
                console.log(data)
            }
        })
    },
    delete: function(ids) {
        if (typeof ids != 'undefined') {
            $.ajax({
                url: VARS.xhr + '/notifications',
                type: 'DELETE',
                data: JSON.stringify({'ids': ids}),
                success: function(data) {
                    console.log(data)
                }
            });
        } else {
            $.ajax({
                url: VARS.xhr + '/notifications',
                type: 'DELETE',
                success: function(data) {
                    console.log(data)
                }
            });
        }
    }
}