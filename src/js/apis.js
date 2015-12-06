let APIS = {

    // POSTS
    posts: {
        create(content, attachments=[], post=undefined, image=undefined) {
            let fd = new FormData(), params;

            // Add the attachments and content to the FormData instance
            for (let attachment of attachments)
                if (attachment) // Can be null
                    fd.append('attachment', attachment.file);

            if (data.content)
                fd.append('content', data.content);

            // Id and type of the base item
            if (image) fd.append('image', image);
            else if (post) fd.append('post', post);

            return $.ajax({
                type: 'POST',
                url:  `${ VARS.xhr }/posts`,
                data: fd,
                processData: false,
                contentType: false,
            });

        }, load(data) {
            return $.ajax({
                url: `${ VARS.xhr }/posts?${ $.param(data)} `,
            });
        }, delete(ids) {
            return $.ajax({
                url: `${ VARS.xhr }/posts?ids=${ JSON.stringify(ids) }`,
                type: 'DELETE',
            });
        }
    },

    // IMAGES

    images: {
        load(data) {
            return $.ajax({
                url: `${ VARS.xhr }/images?${ $.param(data) }`,
            });
        }, upload(files=[], url=null, id=null, set=null) {
            let fd = new FormData();

            // Add images to the FormData instance

            for (let file of files) 
                fd.append('image', file);

            let params = $.param({ url: url, id: id, set: set });

            return $.ajax({
                url: `${ VARS.xhr }/images?${ params }`,
                type: 'POST',
                data: fd,
                processData: false,
                contentType: false,
            });
        }, delete(ids) {
            return $.ajax({
                url: `${ VARS.xhr }/images?ids=${ JSON.stringify(ids) }`,
                type: 'DELETE',
            });
        }
    },

    // ACCOUNTS

    account_data: {
        get(data) {
            return $.ajax({
                url: `${ VARS.xhr }/records?${ $.param(data) }`,
            });
        }, update(data) {
            return $.ajax({
                type: 'PUT',
                url: `${ VARS.xhr }/records/set`, // Empty values will be eliminated anyway
                data: JSON.stringify(data),
            });
        }, unset(data) {
            return $.ajax({
                url: `${ VARS.xhr }/records/unset`,
                type: 'PUT',
                data: JSON.stringify(data), // Do we need this?
            });
        }
    },

    // NOTIFICATIONS

    notifications : {
        get(data) {
            return $.ajax({
                url: `${ VARS.xhr }/notifications`,
            });
        }, delete(ids=null) {
            if (ids !== null) return $.ajax({
                url: `${ VARS.xhr }/notifications`,
                type: 'DELETE',
                data: JSON.stringify({'ids': ids}),
            });
            else return $.ajax({
                url: `${ VARS.xhr }/notifications`,
                type: 'DELETE',
            });
        }
    }
};