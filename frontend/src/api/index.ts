import request from '../utils/request';

export const fetchData = () => {
    return request({
        url: './table.json',
        method: 'get'
    });
};

// 规范数据类型
interface LoginInfo {
	username: string;
	password: string;
}

export const login = (data:LoginInfo) => {
    return request({
        url: 'https://www.fastmock.site/mock/7fbb9df1febbca8eea1742599adec374/test/login',
        method: 'post',
        data
    });
};

export const fetchExcellentBarData = () => {
    return request({
        url:'proxy/apis/v1/excellentInfoHist',
        method: 'get'
    });
};

export const fetchExcellentLineData = () => {
    return request({
        url: 'proxy/apis/v1/excellentInfoLine',
        method: 'get'
    });
};

export const fetchCoursesData = (term:String) => {
    return request({
        url: 'proxy/apis/v1/scores/courses/<term>',
        method: 'post',
        data:{
            "term":term
        }
    });
};

export const fetchGradesData = (term:String) => {
    return request({
        url: 'proxy/apis/v1/scores/grade/<term>',
        method: 'post',
        data:{
            "term":term
        }
    });
};

export const fetchClassesData = (term:String) => {
    return request({
        url: 'proxy/apis/v1/scores/class/chart/<term>',
        method: 'post',
        data:{
            "term":term
        }
    });
};

export const fetchStudntInfoData = (term:String) => {
    return request({
        url: 'proxy/apis/v1/studentInfo/grade/?grade='+term,
        method: 'get'
    });
};