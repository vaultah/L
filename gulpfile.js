var gulp = require('gulp'),
    babel = require('gulp-babel'),
    uglify = require('gulp-uglify'),
    sourcemaps = require('gulp-sourcemaps'),
    jshint = require('gulp-jshint');

gulp.task('js', function() {
    return gulp.src(['public/assets/js/*.js'])
               // .pipe(sourcemaps.init())
               .pipe(jshint({ esnext: true }))
			   .pipe(jshint.reporter('default', { verbose: true }))
               .pipe(babel())
               .pipe(uglify())
               // .pipe(sourcemaps.write())
               .pipe(gulp.dest('dist'));
});

gulp.task('default', ['js']);